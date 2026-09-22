import os
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

METRIC_VERSION = 1
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("DAG_DB_PATH", os.path.join(BASE_DIR, "data", "executions.db"))

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS workflow_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_id INTEGER NOT NULL,
    workflow_name TEXT NOT NULL,
    workers INTEGER NOT NULL,
    strategy TEXT NOT NULL,
    status TEXT NOT NULL,
    metric_version INTEGER NOT NULL DEFAULT 1,
    started_at INTEGER NOT NULL,
    finished_at INTEGER,
    duration_ms INTEGER
);

CREATE INDEX IF NOT EXISTS idx_workflow_runs_started_at
    ON workflow_runs(started_at);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_status
    ON workflow_runs(status);

CREATE TABLE IF NOT EXISTS task_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    task_id TEXT NOT NULL,
    task_name TEXT NOT NULL,
    status TEXT NOT NULL,
    attempts INTEGER NOT NULL,
    started_at INTEGER NOT NULL,
    finished_at INTEGER NOT NULL,
    duration_ms INTEGER NOT NULL CHECK(duration_ms >= 0),
    metric_version INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY(run_id) REFERENCES workflow_runs(id),
    UNIQUE(run_id, task_id)
);

CREATE INDEX IF NOT EXISTS idx_task_runs_started_at
    ON task_runs(started_at);
CREATE INDEX IF NOT EXISTS idx_task_runs_filter
    ON task_runs(run_id, task_id, status);

CREATE TRIGGER IF NOT EXISTS task_runs_immutable_update
BEFORE UPDATE ON task_runs
BEGIN
    SELECT RAISE(ABORT, 'task_runs is append-only and must not be rewritten');
END;

CREATE TRIGGER IF NOT EXISTS task_runs_immutable_delete
BEFORE DELETE ON task_runs
BEGIN
    SELECT RAISE(ABORT, 'task_runs is append-only and must not be deleted');
END;

CREATE TRIGGER IF NOT EXISTS workflow_runs_finalized_update
BEFORE UPDATE ON workflow_runs
WHEN OLD.finished_at IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'finalized workflow_runs must not be rewritten');
END;

CREATE TRIGGER IF NOT EXISTS workflow_runs_finalized_delete
BEFORE DELETE ON workflow_runs
WHEN OLD.finished_at IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'finalized workflow_runs must not be deleted');
END;
"""


def now_ms() -> int:
    return int(time.time() * 1000)


def iso_time(value_ms: Optional[int]) -> Optional[str]:
    if value_ms is None:
        return None
    dt = datetime.fromtimestamp(value_ms / 1000, tz=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA_SQL)
        if conn.execute("PRAGMA user_version").fetchone()[0] == 0:
            conn.execute(f"PRAGMA user_version = {METRIC_VERSION}")


def create_workflow_run(workflow_id: int, workflow_name: str, workers: int, strategy: str) -> int:
    started_at = now_ms()
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO workflow_runs
                (workflow_id, workflow_name, workers, strategy, status, metric_version, started_at)
            VALUES (?, ?, ?, ?, 'RUNNING', ?, ?)
            """,
            (workflow_id, workflow_name, workers, strategy, METRIC_VERSION, started_at),
        )
        return int(cursor.lastrowid)


def insert_task_run(
    run_id: int,
    task_id: str,
    task_name: str,
    status: str,
    attempts: int,
    started_at: int,
    finished_at: int,
) -> None:
    """Insert one finalized stage. The row is never updated after commit."""
    duration_ms = max(0, finished_at - started_at)
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO task_runs
                (run_id, task_id, task_name, status, attempts,
                 started_at, finished_at, duration_ms, metric_version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                task_id,
                task_name,
                status,
                attempts,
                started_at,
                finished_at,
                duration_ms,
                METRIC_VERSION,
            ),
        )


def complete_workflow_run(run_id: int, status: str) -> None:
    finished_at = now_ms()
    with connect() as conn:
        row = conn.execute(
            "SELECT started_at FROM workflow_runs WHERE id = ?", (run_id,)
        ).fetchone()
        if row is None:
            return
        duration_ms = max(0, finished_at - int(row["started_at"]))
        conn.execute(
            """
            UPDATE workflow_runs
               SET status = ?, finished_at = ?, duration_ms = ?
             WHERE id = ? AND finished_at IS NULL
            """,
            (status, finished_at, duration_ms, run_id),
        )


def parse_time(value: Optional[str], *, end_of_day: bool = False) -> Optional[int]:
    if value is None or value == "":
        return None
    text = value.strip()
    if text.isdigit():
        number = int(text)
        return number if number > 10_000_000_000 else number * 1000

    parsed = text
    if len(parsed) == 10:
        parsed += "T23:59:59.999000+00:00" if end_of_day else "T00:00:00+00:00"
    elif end_of_day and len(parsed) == 16:
        parsed += ":59.999000+00:00"
    if parsed.endswith("Z"):
        parsed = parsed[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(parsed)
    except ValueError as exc:
        raise ValueError(f"invalid time: {value}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _base_where(
    start_ms: Optional[int],
    end_ms: Optional[int],
    status: Optional[str],
    task_id: Optional[str] = None,
) -> Tuple[List[str], List[Any]]:
    clauses: List[str] = []
    params: List[Any] = []
    if start_ms is not None:
        clauses.append("r.started_at >= ?")
        params.append(start_ms)
    if end_ms is not None:
        clauses.append("r.started_at <= ?")
        params.append(end_ms)
    if status:
        clauses.append("tr.status = ?")
        params.append(status)
    if task_id:
        clauses.append("tr.task_id = ?")
        params.append(task_id)
    return clauses, params


def _where_sql(clauses: List[str]) -> str:
    return " WHERE " + " AND ".join(clauses) if clauses else ""


def _task_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "runId": row["run_id"],
        "workflowId": row["workflow_id"],
        "workflowName": row["workflow_name"],
        "workers": row["workers"],
        "strategy": row["strategy"],
        "runStatus": row["run_status"],
        "taskId": row["task_id"],
        "taskName": row["task_name"],
        "status": row["status"],
        "attempts": row["attempts"],
        "startedAt": iso_time(row["started_at"]),
        "finishedAt": iso_time(row["finished_at"]),
        "durationMs": row["duration_ms"],
        "metricVersion": row["metric_version"],
    }


def get_execution_report(
    start_ms: Optional[int],
    end_ms: Optional[int],
    task_id: Optional[str],
    status: Optional[str],
    page: int,
    page_size: int,
) -> Dict[str, Any]:
    page = max(1, page)
    page_size = min(100, max(1, page_size))
    task_id = task_id or None
    status = status or None

    filtered_clauses, filtered_params = _base_where(start_ms, end_ms, status, task_id)
    option_clauses, option_params = _base_where(start_ms, end_ms, None)
    option_where = _where_sql(option_clauses)
    filtered_where = _where_sql(filtered_clauses)
    offset = (page - 1) * page_size

    with connect() as conn:
        # One deferred read transaction gives summary, stages and items the same
        # SQLite snapshot even if another workflow finishes during this request.
        conn.execute("BEGIN")
        total = int(
            conn.execute(
                f"SELECT COUNT(*) FROM task_runs tr JOIN workflow_runs r ON r.id = tr.run_id{filtered_where}",
                filtered_params,
            ).fetchone()[0]
        )

        summary_row = conn.execute(
            f"""
            SELECT COUNT(*) AS total_records,
                   COUNT(DISTINCT run_id) AS total_runs,
                   SUM(CASE WHEN tr.status = 'SUCCESS' THEN 1 ELSE 0 END) AS success_count,
                   SUM(CASE WHEN tr.status = 'FAILED' THEN 1 ELSE 0 END) AS failed_count,
                   SUM(tr.duration_ms) AS total_duration_ms,
                   ROUND(AVG(tr.duration_ms)) AS avg_duration_ms,
                   MIN(tr.duration_ms) AS min_duration_ms,
                   MAX(tr.duration_ms) AS max_duration_ms
              FROM task_runs tr
              JOIN workflow_runs r ON r.id = tr.run_id
            {filtered_where}
            """,
            filtered_params,
        ).fetchone()

        stage_rows = conn.execute(
            f"""
            SELECT tr.task_id AS task_id,
                   tr.task_name AS task_name,
                   COUNT(*) AS count,
                   SUM(CASE WHEN tr.status = 'SUCCESS' THEN 1 ELSE 0 END) AS success_count,
                   SUM(CASE WHEN tr.status = 'FAILED' THEN 1 ELSE 0 END) AS failed_count,
                   SUM(tr.duration_ms) AS total_duration_ms,
                   ROUND(AVG(tr.duration_ms)) AS avg_duration_ms,
                   MIN(tr.duration_ms) AS min_duration_ms,
                   MAX(tr.duration_ms) AS max_duration_ms
              FROM task_runs tr
              JOIN workflow_runs r ON r.id = tr.run_id
            {filtered_where}
             GROUP BY tr.task_id, tr.task_name
             ORDER BY MIN(tr.started_at), tr.task_id, tr.task_name
            """,
            filtered_params,
        ).fetchall()

        item_rows = conn.execute(
            f"""
            SELECT tr.id, tr.run_id, r.workflow_id, r.workflow_name, r.workers,
                   r.strategy, r.status AS run_status, tr.task_id, tr.task_name,
                   tr.status, tr.attempts, tr.started_at, tr.finished_at,
                   tr.duration_ms, tr.metric_version
              FROM task_runs tr
              JOIN workflow_runs r ON r.id = tr.run_id
            {filtered_where}
             ORDER BY r.started_at DESC, tr.started_at DESC, tr.id DESC
             LIMIT ? OFFSET ?
            """,
            filtered_params + [page_size, offset],
        ).fetchall()

        option_rows = conn.execute(
            f"""
            SELECT DISTINCT tr.task_id, tr.task_name
              FROM task_runs tr
              JOIN workflow_runs r ON r.id = tr.run_id
            {option_where}
             ORDER BY tr.task_id, tr.task_name
            """,
            option_params,
        ).fetchall()
        conn.commit()

    summary = {
        "totalRecords": int(summary_row["total_records"] or 0),
        "totalRuns": int(summary_row["total_runs"] or 0),
        "successCount": int(summary_row["success_count"] or 0),
        "failedCount": int(summary_row["failed_count"] or 0),
        "totalDurationMs": int(summary_row["total_duration_ms"] or 0),
        "avgDurationMs": int(summary_row["avg_duration_ms"] or 0),
        "minDurationMs": int(summary_row["min_duration_ms"] or 0),
        "maxDurationMs": int(summary_row["max_duration_ms"] or 0),
        "metricVersion": METRIC_VERSION,
    }
    stages = [
        {
            "taskId": row["task_id"],
            "taskName": row["task_name"],
            "count": int(row["count"]),
            "successCount": int(row["success_count"] or 0),
            "failedCount": int(row["failed_count"] or 0),
            "totalDurationMs": int(row["total_duration_ms"] or 0),
            "avgDurationMs": int(row["avg_duration_ms"] or 0),
            "minDurationMs": int(row["min_duration_ms"] or 0),
            "maxDurationMs": int(row["max_duration_ms"] or 0),
        }
        for row in stage_rows
    ]

    return {
        "filters": {
            "startTime": iso_time(start_ms),
            "endTime": iso_time(end_ms),
            "taskId": task_id,
            "status": status,
            "page": page,
            "pageSize": page_size,
        },
        "pagination": {
            "page": page,
            "pageSize": page_size,
            "total": total,
            "totalPages": max(1, (total + page_size - 1) // page_size),
        },
        "summary": summary,
        "stages": stages,
        "items": [_task_to_dict(row) for row in item_rows],
        "taskOptions": [
            {"taskId": row["task_id"], "taskName": row["task_name"]} for row in option_rows
        ],
    }
