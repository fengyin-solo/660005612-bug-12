"""Canonical DAG definition shared by live execution and historical seeding."""
from collections import defaultdict, deque

TASK_DEFS = [
    {"id": "extract", "name": "数据提取", "deps": [], "duration": 2.0},
    {"id": "validate", "name": "数据校验", "deps": ["extract"], "duration": 1.5},
    {"id": "clean_a", "name": "清洗分支A", "deps": ["validate"], "duration": 1.8},
    {"id": "clean_b", "name": "清洗分支B", "deps": ["validate"], "duration": 1.2},
    {"id": "transform", "name": "数据转换", "deps": ["clean_a"], "duration": 3.0},
    {"id": "enrich", "name": "数据增强", "deps": ["clean_a", "clean_b"], "duration": 2.0},
    {"id": "aggregate", "name": "聚合计算", "deps": ["transform", "enrich"], "duration": 2.5},
    {"id": "quality", "name": "质量检查", "deps": ["aggregate"], "duration": 1.0},
    {"id": "export_db", "name": "入库", "deps": ["quality"], "duration": 1.8},
    {"id": "export_report", "name": "报表生成", "deps": ["quality"], "duration": 2.2},
    {"id": "notify", "name": "通知", "deps": ["export_db", "export_report"], "duration": 0.5},
]

POSITIONS = [
    (0, 0), (0, 1), (-1, 2), (1, 2), (-1, 3),
    (0.5, 3), (-0.3, 4), (-0.3, 5), (-1, 6), (0.5, 6), (-0.3, 7),
]


def topological_order(nodes):
    in_degree = {n["id"]: 0 for n in nodes}
    for n in nodes:
        for d in n["deps"]:
            in_degree[n["id"]] += 1
    ready = deque([tid for tid, deg in in_degree.items() if deg == 0])
    order = []
    while ready:
        tid = ready.popleft()
        order.append(tid)
        for n in nodes:
            if tid in n["deps"]:
                in_degree[n["id"]] -= 1
                if in_degree[n["id"]] == 0:
                    ready.append(n["id"])
    return order


def generate_dag_workflow(name: str):
    """Create a realistic DAG pipeline."""
    nodes = []
    for i, td in enumerate(TASK_DEFS):
        n = dict(td)
        n["x"] = POSITIONS[i][0] * 2.5 + 2.5
        n["y"] = POSITIONS[i][1] * 0.9
        n["status"] = "PENDING"
        n["retries"] = 0
        n["startTime"] = None
        n["endTime"] = None
        nodes.append(n)

    edges = []
    for n in nodes:
        for d in n["deps"]:
            edges.append([d, n["id"]])

    return {
        "nodes": [{
            "id": n["id"], "name": n["name"], "deps": n["deps"],
            "x": n["x"], "y": n["y"], "status": n["status"],
            "startTime": None, "endTime": None, "retries": n["retries"],
        } for n in nodes],
        "edges": edges,
        "durations": {n["id"]: n["duration"] for n in nodes},
    }
