"""SQLite persistence for completed workflow executions.

A finished execution is frozen here as an immutable snapshot. Reports and the
detail list MUST read through the same query helpers in this module so that the
two pages can never disagree about row counts or durations.
"""
import json
import os
import sqlite3
import threading
import time

DB_PATH = os.environ.get("DAG_DB_PATH", os.path.join(os.path.dirname(__file__), "runs.db"))

_lock = threading.Lock()


def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _lock, _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY,
                workflow_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                workers INTEGER NOT NULL,
                strategy TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at REAL NOT NULL,
                ended_at REAL NOT NULL,
                duration REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS task_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                task_id TEXT NOT NULL,
                task_name TEXT NOT NULL,
                status TEXT NOT NULL,
                attempts INTEGER NOT NULL,
                started_at REAL NOT NULL,
                ended_at REAL NOT NULL,
                duration REAL NOT NULL,
                seq INTEGER NOT NULL,
                UNIQUE(run_id, task_id)
            );
            """
        )


def save_run(workflow_id, name, workers, strategy, status, started_at, nodes, seq_order):
    """Freeze one completed run. Historical rows are never rewritten.

    ``nodes`` is the final node list; every node is expected to carry its
    original ``startTime`` (the first attempt) and ``endTime``.
    """
    ended_at = time.time()
    seq_map = {tid: i for i, tid in enumerate(seq_order)}
    with _lock, _connect() as conn:
        cur = conn.execute(
            "INSERT INTO runs(workflow_id, name, workers, strategy, status, started_at, ended_at, duration)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (workflow_id, name, workers, strategy, status, started_at, ended_at,
             round(max((n["endTime"] for n in nodes if n.get("endTime")), default=ended_at) - started_at, 3)),
        )
        run_id = cur.lastrowid
        for n in nodes:
            st = n.get("startTime") or started_at
            et = n.get("endTime") or st
            conn.execute(
                "INSERT INTO task_runs(run_id, task_id, task_name, status, attempts, started_at, ended_at, duration, seq)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (run_id, n["id"], n["name"], n["status"], max(1, n.get("retries", 0) + 1),
                 st, et, round(et - st, 3), seq_map.get(n["id"], len(seq_map))),
            )
    return run_id


def _build_where(start, end, status, workflow_id):
    """The single source of truth for the time-range / status filter."""
    where, params = ["1=1"], []
    if start is not None:
        where.append("r.started_at >= ?")
        params.append(start)
    if end is not None:
        where.append("r.started_at < ?")
        params.append(end)
    if status:
        where.append("r.status = ?")
        params.append(status)
    if workflow_id is not None:
        where.append("r.workflow_id = ?")
        params.append(workflow_id)
    return " AND ".join(where), params


def query_runs(start=None, end=None, status=None, workflow_id=None, limit=500):
    """Detail list: every run matching the filter. This is the shared base set."""
    where, params = _build_where(start, end, status, workflow_id)
    sql = (
        "SELECT r.*, "
        "(SELECT COUNT(*) FROM task_runs t WHERE t.run_id = r.id AND t.status != 'SKIPPED') AS task_count, "
        "(SELECT COALESCE(SUM(t.duration),0) FROM task_runs t WHERE t.run_id = r.id AND t.status != 'SKIPPED') AS task_duration_sum "
        "FROM runs r WHERE " + where + " ORDER BY r.started_at DESC LIMIT ?"
    )
    params.append(limit)
    with _lock, _connect() as conn:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]


def query_report(start=None, end=None, status=None, workflow_id=None):
    """Report: aggregate over EXACTLY the same filtered run set as query_runs."""
    where, params = _build_where(start, end, status, workflow_id)
    with _lock, _connect() as conn:
        total = conn.execute(
            "SELECT COUNT(*) AS c, COALESCE(AVG(duration),0) AS avg_duration,"
            " COALESCE(SUM(duration),0) AS total_duration FROM runs r WHERE " + where,
            params,
        ).fetchone()
        status_rows = conn.execute(
            "SELECT r.status AS status, COUNT(*) AS count, COALESCE(SUM(r.duration),0) AS duration"
            " FROM runs r WHERE " + where + " GROUP BY r.status",
            params,
        ).fetchall()
        # Per-stage (task) metrics, joined so the join inherits the identical filter.
        task_rows = conn.execute(
            "SELECT t.task_id AS task_id, t.task_name AS task_name, t.status AS status,"
            " COUNT(*) AS count, COALESCE(SUM(t.duration),0) AS duration,"
            " COALESCE(AVG(t.duration),0) AS avg_duration, MAX(t.seq) AS seq"
            " FROM task_runs t JOIN runs r ON r.id = t.run_id WHERE " + where +
            " GROUP BY t.task_id, t.task_name, t.status ORDER BY MAX(t.seq)",
            params,
        ).fetchall()
    return {
        "runCount": total["c"],
        "avgDuration": round(total["avg_duration"], 3),
        "totalDuration": round(total["total_duration"], 3),
        "byStatus": [dict(r) for r in status_rows],
        "tasks": [dict(r) for r in task_rows],
    }


def get_run(run_id):
    with _lock, _connect() as conn:
        run = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if not run:
            return None
        tasks = conn.execute(
            "SELECT * FROM task_runs WHERE run_id = ? ORDER BY seq", (run_id,)
        ).fetchall()
    return {"run": dict(run), "tasks": [dict(t) for t in tasks]}


def seed_if_empty():
    """Insert a fixed set of historical runs so the pages have data on first boot.

    Data is fully deterministic (no RNG): historical records must never change
    on later boots, and this is a no-op once any run exists.
    """
    with _lock, _connect() as conn:
        if conn.execute("SELECT COUNT(*) AS c FROM runs").fetchone()["c"]:
            return
    from .workflow import TASK_DEFS

    now = time.time()
    day = 86400
    # (days_ago, workers, strategy, run_status, overrides per task index: status)
    scenarios = [
        (0.2, 3, "fifo", "SUCCESS", {}),
        (0.8, 5, "fifo", "SUCCESS", {}),
        (1.4, 3, "priority", "SUCCESS", {3: "FAILED"}),
        (2.1, 1, "fifo", "FAILED", {6: "FAILED", 7: "FAILED"}),
        (3.5, 5, "max_concurrent", "SUCCESS", {}),
        (5.2, 3, "fifo", "SUCCESS", {9: "FAILED"}),
        (7.8, 3, "priority", "SUCCESS", {}),
        (11.0, 1, "fifo", "FAILED", {4: "FAILED", 5: "FAILED", 6: "FAILED"}),
        (14.5, 5, "fifo", "SUCCESS", {}),
        (20.0, 3, "fifo", "SUCCESS", {2: "FAILED"}),
    ]
    for i, (days_ago, workers, strategy, run_status, failed_idx) in enumerate(scenarios):
        started_at = now - days_ago * day
        nodes, cursor = [], started_at
        for idx, td in enumerate(TASK_DEFS):
            st_status = "FAILED" if idx in failed_idx else "SUCCESS"
            attempts = 3 if st_status == "FAILED" else (2 if idx % 4 == 0 else 1)
            duration = round(td["duration"] * (0.9 + 0.03 * (i + idx)), 3)
            nodes.append({
                "id": td["id"], "name": td["name"], "status": st_status,
                "retries": attempts - 1,
                "startTime": round(cursor, 3), "endTime": round(cursor + duration, 3),
            })
            cursor += duration * 0.85  # overlap: parallel branches
        save_run(1000 + i, "data-pipeline", workers, strategy, run_status,
                 started_at, nodes, [td["id"] for td in TASK_DEFS])
