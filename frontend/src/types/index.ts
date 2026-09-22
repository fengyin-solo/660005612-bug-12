export interface TaskNode { id: string; name: string; deps: string[]; x: number; y: number; status: string; startTime?: number; endTime?: number; retries: number }
export interface DAGWorkflow { id: number; name: string; nodes: TaskNode[]; edges: [string,string][] }
export interface ExecutionLog { taskId: string; status: string; timestamp: number; message: string }
export interface CircuitBreaker { taskId: string; failureCount: number; state: string; cooldownUntil: number }
export interface ExecutionInfo { workflow: DAGWorkflow; logs: ExecutionLog[]; circuitBreakers: CircuitBreaker[]; completed: boolean }

export interface RunItem {
  id: number
  workflow_id: number
  name: string
  workers: number
  strategy: string
  status: string
  started_at: number
  ended_at: number
  duration: number
  task_count: number
  task_duration_sum: number
}

export interface TaskRun {
  id: number
  run_id: number
  task_id: string
  task_name: string
  status: string
  attempts: number
  started_at: number
  ended_at: number
  duration: number
  seq: number
}

export interface RunDetail { run: RunItem; tasks: TaskRun[] }

export interface ReportData {
  runCount: number
  avgDuration: number
  totalDuration: number
  byStatus: { status: string; count: number; duration: number }[]
  tasks: {
    task_id: string; task_name: string; status: string
    count: number; duration: number; avg_duration: number; seq: number
  }[]
}

/** The one filter contract shared by the report and the detail list. */
export interface RunFilter { start?: number; end?: number; status?: string }
