import asyncio
import json
import random
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import db
from .workflow import generate_dag_workflow, topological_order

ACTIVE_CLIENTS = []
WORKFLOW_ID = 0
_loop = None  # main-thread event loop, captured for thread-safe WS pushes


class WorkflowCreate(BaseModel):
    name: str = "data-pipeline"


class RunRequest(BaseModel):
    workflowId: int
    workers: int = 3
    strategy: str = "fifo"


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _loop
    _loop = asyncio.get_running_loop()
    db.init_db()
    db.seed_if_empty()
    yield


app = FastAPI(title="DAG Workflow Engine", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.post("/api/workflow")
def create_workflow(req: WorkflowCreate):
    global WORKFLOW_ID
    WORKFLOW_ID += 1
    dag = generate_dag_workflow(req.name)
    return {"id": WORKFLOW_ID, "name": req.name, "nodes": dag["nodes"], "edges": dag["edges"],
            "_durations": dag["durations"]}


@app.post("/api/run")
def run_workflow(req: RunRequest):
    dag = generate_dag_workflow("workflow")
    t = threading.Thread(target=execute_workflow,
                         args=(req.workflowId, dag, req.workers, req.strategy), daemon=True)
    t.start()
    return {
        "workflow": {"id": req.workflowId, "name": "workflow", "nodes": dag["nodes"], "edges": dag["edges"]},
        "logs": [], "circuitBreakers": [], "completed": False
    }


def execute_workflow(workflow_id, dag, workers, strategy):
    nodes = dag["nodes"]
    durations = dag["durations"]
    edges = dag["edges"]
    seq_order = topological_order(nodes)
    run_started_at = time.time()
    in_degree = defaultdict(int)
    adj = defaultdict(list)
    for u, v in edges:
        in_degree[v] += 1
        adj[u].append(v)

    # BFS topological sort
    ready = deque([n["id"] for n in nodes if in_degree[n["id"]] == 0])
    node_map = {n["id"]: n for n in nodes}
    logs = []
    cb_state = defaultdict(lambda: {"failureCount": 0, "state": "CLOSED", "cooldownUntil": 0})
    failure_threshold = 3
    running_tasks = {}
    completed = set()
    failed = set()

    def send_update(completed_flag=False):
        payload = {
            "workflow": {"id": workflow_id, "name": "workflow", "nodes": nodes, "edges": edges},
            "logs": logs[-30:],
            "circuitBreakers": [{"taskId": k, **v} for k, v in cb_state.items()],
            "completed": completed_flag
        }
        for ws in list(ACTIVE_CLIENTS):
            try:
                asyncio.run_coroutine_threadsafe(ws.send_text(json.dumps(payload)), _loop)
            except Exception:
                pass
        time.sleep(0.3)

    while ready or running_tasks:
        # Start tasks
        while ready and len(running_tasks) < workers:
            tid = ready.popleft()
            node = node_map[tid]
            cb = cb_state[tid]
            if cb["state"] == "OPEN" and time.time() < cb["cooldownUntil"]:
                ready.appendleft(tid)
                continue
            if cb["state"] == "OPEN":
                cb["state"] = "HALF_OPEN"

            node["status"] = "RUNNING"
            # Keep the FIRST attempt's start time: duration must cover retries too,
            # otherwise retried nodes report 0 / wildly wrong durations.
            if node.get("startTime") is None:
                node["startTime"] = time.time()

            # Simulate task execution (random success/failure)
            will_fail = random.random() < 0.12  # 12% failure rate
            runtime = durations.get(tid, 1.5) * random.uniform(0.7, 1.3)
            running_tasks[tid] = {
                "end_time": time.time() + runtime,
                "will_fail": will_fail,
            }
            logs.append({"taskId": tid, "status": "RUNNING", "timestamp": time.time(),
                         "message": f"开始执行 {node['name']}"})

        # Check completed tasks
        now = time.time()
        finished = []
        for tid, info in running_tasks.items():
            if now >= info["end_time"]:
                node = node_map[tid]
                if info["will_fail"] and node["retries"] < 3:
                    node["retries"] += 1
                    # Back to the queue, but startTime stays as the first attempt.
                    node["status"] = "PENDING"
                    ready.appendleft(tid)
                    cb = cb_state[tid]
                    cb["failureCount"] += 1
                    logs.append({"taskId": tid, "status": "FAILED", "timestamp": now,
                                 "message": f"重试 {node['retries']}/3"})
                    if cb["failureCount"] >= failure_threshold:
                        cb["state"] = "OPEN"
                        cb["cooldownUntil"] = now + 5
                        logs.append({"taskId": tid, "status": "CIRCUIT_OPEN", "timestamp": now,
                                     "message": f"熔断! {failure_threshold}次连续失败"})
                else:
                    node["endTime"] = now
                    if info["will_fail"]:
                        node["status"] = "FAILED"
                        failed.add(tid)
                    else:
                        node["status"] = "SUCCESS"
                        completed.add(tid)
                    cb_state[tid]["failureCount"] = 0
                    cb_state[tid]["state"] = "CLOSED"
                    logs.append({"taskId": tid, "status": node["status"], "timestamp": now,
                                 "message": f"完成 {node['name']}"})
                    # Downstream only unlocks on success; a failed branch ends the run.
                    if node["status"] == "SUCCESS":
                        for next_tid in adj[tid]:
                            in_degree[next_tid] -= 1
                            if in_degree[next_tid] == 0:
                                ready.append(next_tid)
                finished.append(tid)

        for tid in finished:
            del running_tasks[tid]

        send_update()
        if len(completed) + len(failed) == len(nodes):
            break
        if failed and not ready and not running_tasks:
            break

    # Any node that never ran (blocked by an upstream failure) is frozen as
    # SKIPPED — it must not masquerade as a real 0-second execution.
    final_now = time.time()
    for n in nodes:
        if n.get("startTime") is None:
            n["startTime"] = final_now
            n["endTime"] = final_now
            n["status"] = "SKIPPED"
        elif n.get("endTime") is None:
            n["endTime"] = final_now
            if n["status"] not in ("FAILED", "SUCCESS"):
                n["status"] = "FAILED" if failed else "SUCCESS"

    run_status = "FAILED" if failed else "SUCCESS"
    # Freeze an immutable snapshot: later filter/caliber changes never rewrite it.
    db.save_run(workflow_id, "data-pipeline", workers, strategy, run_status,
                run_started_at, nodes, seq_order)
    send_update(True)


def parse_ts(value):
    """Accept epoch seconds or ISO strings; None passes through."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail=f"invalid timestamp: {value}")


@app.get("/api/runs")
def list_runs(
    start: float = Query(None),
    end: float = Query(None),
    status: str = Query(None),
    workflowId: int = Query(None),
):
    """Detail list data — same filter contract as /api/report."""
    return {"items": db.query_runs(parse_ts(start), parse_ts(end), status, workflowId)}


@app.get("/api/report")
def report(
    start: float = Query(None),
    end: float = Query(None),
    status: str = Query(None),
    workflowId: int = Query(None),
):
    """Aggregated report over the identical base set returned by /api/runs."""
    return db.query_report(parse_ts(start), parse_ts(end), status, workflowId)


@app.get("/api/runs/{run_id}")
def run_detail(run_id: int):
    data = db.get_run(run_id)
    if not data:
        raise HTTPException(status_code=404, detail="run not found")
    return data


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    ACTIVE_CLIENTS.append(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if ws in ACTIVE_CLIENTS:
            ACTIVE_CLIENTS.remove(ws)
