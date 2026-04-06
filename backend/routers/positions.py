import json
from fastapi import APIRouter
from backend.database import get_db
from backend.services.fx import get_usd_gbp_rate
from backend.validators import PositionEntry, ClosePositionPayload

router = APIRouter(prefix="/api/positions", tags=["positions"])


@router.get("")
def get_positions():
    with get_db() as db:
        rows = db.execute("SELECT * FROM positions ORDER BY entry_date DESC").fetchall()
    return [dict(r) for r in rows]


@router.get("/open")
def get_open_positions():
    with get_db() as db:
        rows = db.execute("SELECT * FROM positions WHERE status = 'OPEN' ORDER BY entry_date DESC").fetchall()
    return [dict(r) for r in rows]


@router.get("/summary")
def get_pnl_summary():
    """P&L summary for closed positions."""
    with get_db() as db:
        rows = db.execute("SELECT * FROM positions WHERE status = 'CLOSED'").fetchall()

    total_pnl_gbp = 0
    wins = 0
    losses = 0
    for r in rows:
        if r["position_type"] == "option" and r["premium_paid"] and r["exit_price"] is not None:
            pnl = (r["exit_price"] - r["premium_paid"]) * (r["contracts"] or 1) * 100 * get_usd_gbp_rate()
            total_pnl_gbp += pnl
            if pnl > 0:
                wins += 1
            else:
                losses += 1
        elif r["position_type"] == "stock" and r["avg_price"] and r["exit_price"] is not None:
            pnl = (r["exit_price"] - r["avg_price"]) * (r["shares"] or 0)
            total_pnl_gbp += pnl * get_usd_gbp_rate()
            if pnl > 0:
                wins += 1
            else:
                losses += 1

    return {
        "total_pnl_gbp": round(total_pnl_gbp, 2),
        "total_trades": wins + losses,
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / (wins + losses), 2) if (wins + losses) > 0 else 0,
    }


@router.post("")
def add_position(entry: PositionEntry):
    with get_db() as db:
        db.execute("""
            INSERT INTO positions (ticker, position_type, bucket, shares, avg_price,
                strike, expiry, premium_paid, contracts, thesis, invalidation,
                target_fair_value, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.ticker, entry.position_type, entry.bucket,
            entry.shares, entry.avg_price,
            entry.strike, entry.expiry,
            entry.premium_paid, entry.contracts,
            entry.thesis, json.dumps(entry.invalidation),
            entry.target_fair_value, entry.status,
        ))
        db.commit()
        pos_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    return {"status": "added", "id": pos_id}


@router.put("/{position_id}/close")
def close_position(position_id: int, data: ClosePositionPayload):
    with get_db() as db:
        db.execute("""
            UPDATE positions SET status = 'CLOSED', exit_price = ?, exit_date = date('now'), exit_reason = ?
            WHERE id = ?
        """, (data.exit_price, data.exit_reason, position_id))
        db.commit()
    return {"status": "closed", "id": position_id}
