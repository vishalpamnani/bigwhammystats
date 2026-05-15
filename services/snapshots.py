import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from config import SNAPSHOT_DB_PATH
from services.fpl_service import fetch_all_league_standings, fetch_entry_history


def _connect(db_path: Path = SNAPSHOT_DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_snapshot_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS league_rank_snapshots (
                league_id INTEGER NOT NULL,
                gw INTEGER NOT NULL,
                entry INTEGER NOT NULL,
                player_name TEXT NOT NULL,
                entry_name TEXT NOT NULL,
                rank INTEGER NOT NULL,
                total INTEGER NOT NULL,
                captured_at TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'cumulative_total_points',
                PRIMARY KEY (league_id, gw, entry)
            )
            """
        )
        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(league_rank_snapshots)").fetchall()
        }
        if "source" not in columns:
            conn.execute(
                """
                ALTER TABLE league_rank_snapshots
                ADD COLUMN source TEXT
                """
            )


def load_league_rank_snapshot(league_id: int, gw: int) -> List[Dict[str, Any]]:
    init_snapshot_db()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT entry, player_name, entry_name, rank, total, captured_at
            FROM league_rank_snapshots
            WHERE league_id = ? AND gw = ? AND source = 'cumulative_total_points'
            ORDER BY rank ASC, entry ASC
            """,
            (league_id, gw),
        ).fetchall()

    return [dict(row) for row in rows]


def save_league_rank_snapshot(league_id: int, gw: int, standings: List[Dict[str, Any]]) -> None:
    init_snapshot_db()
    captured_at = datetime.now(timezone.utc).isoformat()
    rows = [
        (
            league_id,
            gw,
            int(row["entry"]),
            row.get("player_name", ""),
            row.get("entry_name", ""),
            int(row["rank"]),
            int(row.get("total", 0)),
            captured_at,
            "cumulative_total_points",
        )
        for row in standings
        if row.get("entry") is not None and row.get("rank") is not None
    ]

    if not rows:
        return

    with _connect() as conn:
        conn.executemany(
            """
            INSERT OR REPLACE INTO league_rank_snapshots
                (league_id, gw, entry, player_name, entry_name, rank, total, captured_at, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


def build_cumulative_league_rank_snapshot(league_id: int, gw: int) -> List[Dict[str, Any]]:
    """
    Build the Big Whammy table as it stood after `gw` using each manager's
    cumulative official FPL total_points after that gameweek.
    """
    standings = fetch_all_league_standings(league_id)
    rows: List[Dict[str, Any]] = []

    for current_row in standings:
        entry = int(current_row["entry"])
        history = fetch_entry_history(entry)
        gw_rows = history.get("current", []) or []
        gw_row = next((row for row in gw_rows if int(row.get("event", 0)) == gw), None)

        if not gw_row:
            continue

        rows.append(
            {
                "entry": entry,
                "player_name": current_row.get("player_name", ""),
                "entry_name": current_row.get("entry_name", ""),
                "total": int(gw_row.get("total_points", 0)),
                # Use current official order only as a stable deterministic fallback
                # when cumulative points are tied.
                "current_rank": int(current_row.get("rank", 10**9)),
            }
        )

    rows.sort(key=lambda row: (-row["total"], row["current_rank"], row["entry"]))

    ranked_rows = []
    previous_total = None
    previous_rank = 0
    for index, row in enumerate(rows, start=1):
        if previous_total is None or row["total"] != previous_total:
            previous_rank = index
            previous_total = row["total"]

        ranked_rows.append(
            {
                "entry": row["entry"],
                "player_name": row["player_name"],
                "entry_name": row["entry_name"],
                "rank": previous_rank,
                "total": row["total"],
            }
        )

    return ranked_rows


def get_or_capture_league_rank_snapshot(
    league_id: int, gw: int, force_refresh: bool = False
) -> List[Dict[str, Any]]:
    if not force_refresh:
        cached = load_league_rank_snapshot(league_id, gw)
        if cached:
            return cached

    standings = build_cumulative_league_rank_snapshot(league_id, gw)
    if standings:
        save_league_rank_snapshot(league_id, gw, standings)
        return load_league_rank_snapshot(league_id, gw)

    return load_league_rank_snapshot(league_id, gw)
