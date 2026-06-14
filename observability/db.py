import sqlite3
from pathlib import Path

_DB_PATH = Path(__file__).parent.parent / "data" / "decisions.db"
_DB_PATH.parent.mkdir(exist_ok=True)

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS decisions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              TEXT,
    step            INTEGER,
    endpoint_name   TEXT,
    endpoint_url    TEXT,
    source          TEXT,
    last_status     TEXT,
    ok_count        INTEGER,
    error_count     INTEGER,
    timeout_count   INTEGER,
    latency_ms      REAL,
    llm_latency_ms  REAL,
    llm_cost_usd    REAL,
    decision        TEXT,
    incident_type   TEXT,
    confidence      REAL
)
"""

_INSERT_SQL = """
INSERT INTO decisions
    (ts, step, endpoint_name, endpoint_url, source, last_status,
     ok_count, error_count, timeout_count, latency_ms,
     llm_latency_ms, llm_cost_usd, decision, incident_type, confidence)
VALUES
    (:ts, :step, :endpoint_name, :endpoint_url, :source, :last_status,
     :ok_count, :error_count, :timeout_count, :latency_ms,
     :llm_latency_ms, :llm_cost_usd, :decision, :incident_type, :confidence)
"""


def init_db() -> None:
    with sqlite3.connect(_DB_PATH) as conn:
        conn.execute(_CREATE_SQL)


def insert_decision(entry: dict) -> None:
    with sqlite3.connect(_DB_PATH) as conn:
        conn.execute(_INSERT_SQL, entry)
