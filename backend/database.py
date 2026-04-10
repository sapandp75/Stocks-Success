import sqlite3
from contextlib import contextmanager
from datetime import datetime
from backend.config import DB_PATH


@contextmanager
def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def is_fresh(fetched_at: str | None, ttl_hours: int) -> bool:
    """Check if a cached value is still fresh. Timezone-naive."""
    if not fetched_at:
        return False
    fetched = datetime.fromisoformat(fetched_at)
    return (datetime.now() - fetched).total_seconds() < ttl_hours * 3600


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_db() as conn:
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
                universe TEXT NOT NULL DEFAULT 'spx',
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
                ai_next_review_date TEXT,
                ai_sections_json TEXT,
                data_completeness TEXT DEFAULT '{}'
            );

            CREATE INDEX IF NOT EXISTS idx_deep_dives_ticker ON deep_dives(ticker, dive_date DESC);
            CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status);
            CREATE INDEX IF NOT EXISTS idx_scan_results_date ON scan_results(scan_date DESC);

            CREATE TABLE IF NOT EXISTS research_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                source TEXT NOT NULL,
                content_type TEXT NOT NULL,
                title TEXT,
                summary TEXT,
                url TEXT,
                published_date TEXT,
                fetched_at TEXT NOT NULL DEFAULT (datetime('now')),
                raw_json TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_research_ticker ON research_cache(ticker, fetched_at DESC);
            CREATE INDEX IF NOT EXISTS idx_research_source ON research_cache(source, ticker);

            CREATE TABLE IF NOT EXISTS sentiment_cache (
                ticker TEXT PRIMARY KEY,
                av_sentiment_score REAL,
                av_sentiment_label TEXT,
                av_article_count INTEGER,
                finnhub_consensus TEXT,
                finnhub_target_mean REAL,
                finnhub_target_high REAL,
                finnhub_target_low REAL,
                finnhub_recent_change TEXT,
                fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS digest_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                event_type TEXT NOT NULL,
                headline TEXT NOT NULL,
                detail TEXT,
                event_date TEXT,
                source TEXT,
                url TEXT,
                fetched_at TEXT NOT NULL DEFAULT (datetime('now')),
                seen INTEGER DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_digest_ticker ON digest_events(ticker, fetched_at DESC);
            CREATE INDEX IF NOT EXISTS idx_digest_unseen ON digest_events(seen, fetched_at DESC);

            CREATE TABLE IF NOT EXISTS technicals_cache (
                ticker TEXT PRIMARY KEY,
                rsi REAL,
                macd_value REAL,
                macd_signal REAL,
                macd_histogram REAL,
                macd_crossover TEXT,
                direction TEXT,
                ema20 REAL,
                sma50 REAL,
                sma200 REAL,
                adx REAL,
                bollinger_upper REAL,
                bollinger_lower REAL,
                bollinger_pct_b REAL,
                volume_relative REAL,
                volume_trend TEXT,
                support_1 REAL,
                support_2 REAL,
                resistance_1 REAL,
                resistance_2 REAL,
                rs_vs_spy_20d REAL,
                rs_vs_spy_60d REAL,
                data_json TEXT,
                fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS financial_history_cache (
                ticker TEXT NOT NULL,
                metric TEXT NOT NULL,
                year INTEGER NOT NULL,
                value REAL,
                fetched_at TEXT NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (ticker, metric, year)
            );

            CREATE TABLE IF NOT EXISTS insider_cache (
                ticker TEXT PRIMARY KEY,
                net_sentiment TEXT,
                data_json TEXT,
                fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS institutional_cache (
                ticker TEXT PRIMARY KEY,
                trend TEXT,
                data_json TEXT,
                fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS analyst_cache (
                ticker TEXT PRIMARY KEY,
                consensus TEXT,
                target_mean REAL,
                target_low REAL,
                target_high REAL,
                num_analysts INTEGER,
                data_json TEXT,
                fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS peer_cache (
                ticker TEXT PRIMARY KEY,
                peers_json TEXT,
                fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS quarterly_cache (
                ticker TEXT PRIMARY KEY,
                data_json TEXT,
                fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS growth_metrics_cache (
                ticker TEXT PRIMARY KEY,
                data_json TEXT,
                fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS forward_estimates_cache (
                ticker TEXT PRIMARY KEY,
                data_json TEXT,
                fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS external_targets_cache (
                ticker TEXT PRIMARY KEY,
                data_json TEXT,
                fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS fund_flow_cache (
                ticker TEXT PRIMARY KEY,
                data_json TEXT,
                fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS fundamentals_cache (
                ticker TEXT PRIMARY KEY,
                data_json TEXT NOT NULL,
                fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)
        _ensure_column(conn, "deep_dives", "ai_next_review_date", "TEXT")
        _ensure_column(conn, "deep_dives", "ai_sections_json", "TEXT")
        _ensure_column(conn, "deep_dives", "snapshot_json", "TEXT")
        _ensure_column(conn, "scan_results", "universe", "TEXT NOT NULL DEFAULT 'spx'")


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    existing = {
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        conn.commit()
