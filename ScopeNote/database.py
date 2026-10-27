import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def connect(db_path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    return connection


def init_db(db_path: str | Path) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS briefs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                project_type TEXT NOT NULL,
                source_text TEXT NOT NULL,
                analysis_json TEXT NOT NULL,
                mode TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.commit()


def save_brief(db_path: str | Path, project_type: str, source_text: str, analysis: dict[str, Any], mode: str) -> int:
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connect(db_path) as connection:
        cursor = connection.execute(
            "INSERT INTO briefs (title, project_type, source_text, analysis_json, mode, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (analysis.get("title") or "Untitled client brief", project_type, source_text, json.dumps(analysis, ensure_ascii=False), mode, created_at),
        )
        connection.commit()
        return int(cursor.lastrowid)


def get_brief(db_path: str | Path, brief_id: int) -> dict[str, Any] | None:
    with connect(db_path) as connection:
        row = connection.execute("SELECT * FROM briefs WHERE id = ?", (brief_id,)).fetchone()
    if row is None:
        return None
    item = dict(row)
    item["analysis"] = json.loads(item.pop("analysis_json"))
    return item


def list_briefs(db_path: str | Path, limit: int = 50) -> list[dict[str, Any]]:
    with connect(db_path) as connection:
        rows = connection.execute(
            "SELECT id, title, project_type, source_text, mode, created_at FROM briefs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def delete_brief(db_path: str | Path, brief_id: int) -> bool:
    with connect(db_path) as connection:
        cursor = connection.execute("DELETE FROM briefs WHERE id = ?", (brief_id,))
        connection.commit()
        return cursor.rowcount > 0
