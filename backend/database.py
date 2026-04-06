import sqlite3
from backend.config import DB_PATH


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS watchlist (
            ticker TEXT PRIMARY KEY,
            bucket TEXT NOT NULL,
            added_date TEXT NOT NULL DEFAULT (date('now')),
            thesis_note TEXT DEFAULT '',
            entry_zone_low REAL,
            entry_zone_high REAL,
            last_deep_dive TEXT,
            conviction TEXT DEFAULT 'MODERATE',
            status TEXT DEFAULT 'WATCHING'
        );

        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            position_type TEXT NOT NULL,
            bucket TEXT DEFAULT 'B1',
            shares REAL,
            avg_price REAL,
            strike REAL,
            expiry TEXT,
            premium_paid REAL,
            contracts INTEGER,
            entry_date TEXT NOT NULL DEFAULT (date('now')),
            thesis TEXT DEFAULT '',
            invalidation TEXT DEFAULT '[]',
            target_fair_value REAL,
            status TEXT DEFAULT 'OPEN',
            exit_price REAL,
            exit_date TEXT,
            exit_reason TEXT
        );

        CREATE TABLE IF NOT EXISTS scan_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_date TEXT NOT NULL DEFAULT (datetime('now')),
            scan_type TEXT NOT NULL DEFAULT 'weekly',
            total_scanned INTEGER,
            b1_count INTEGER,
            b2_count INTEGER,
            results_json TEXT NOT NULL,
            errors_json TEXT DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS deep_dives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            dive_date TEXT NOT NULL DEFAULT (datetime('now')),
            fundamentals_json TEXT,
            reverse_dcf_json TEXT,
            forward_dcf_json TEXT,
            ai_first_impression TEXT,
            ai_bear_case_stock TEXT,
            ai_bear_case_business TEXT,
            ai_bull_case_rebuttal TEXT,
            ai_bull_case_upside TEXT,
            ai_whole_picture TEXT,
            ai_self_review TEXT,
            ai_verdict TEXT,
            ai_conviction TEXT,
            ai_entry_grid_json TEXT,
            ai_exit_playbook TEXT,
            data_completeness TEXT DEFAULT '{}'
        );

        CREATE INDEX IF NOT EXISTS idx_deep_dives_ticker ON deep_dives(ticker, dive_date DESC);
        CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status);
        CREATE INDEX IF NOT EXISTS idx_scan_results_date ON scan_results(scan_date DESC);
    """)
    conn.close()
