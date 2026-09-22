export interface TaskNode { id: string; name: string; deps: string[]; x: number; y: number; status: string; startTime?: number; endTime?: number; retries: number }
export interface DAGWorkflow { id: number; name: string; nodes: TaskNode[]; edges: [string,string][] }
export interface ExecutionLog { taskId: string; status: string; timestamp: number; message: string }
export interface CircuitBreaker { taskId: string; failureCount: number; state: string; cooldownUntil: number }
export interface ExecutionInfo { runId?: number; workflow: DAGWorkflow; logs: ExecutionLog[]; circuitBreakers: CircuitBreaker[]; completed: boolean }

export type PageView = 'workflow' | 'report' | 'detail'
export type StageStatus = '' | 'SUCCESS' | 'FAILED'

export interface ReportFilters {
  startTime: string
  endTime: string
  taskId: string
  status: StageStatus
  page: number
  pageSize: number
}

export interface TaskOption {
  taskId: string
  taskName: string
}

export interface ExecutionRecord {
  id: number
  runId: number
  workflowId: number
  workflowName: string
  workers: number
  strategy: string
  runStatus: string
  taskId: string
  taskName: string
  status: 'SUCCESS' | 'FAILED'
  attempts: number
  startedAt: string
  finishedAt: string
  durationMs: number
  metricVersion: number
}

export interface StageSummary {
  taskId: string
  taskName: string
  count: number
  successCount: number
  failedCount: number
  totalDurationMs: number
  avgDurationMs: number
  minDurationMs: number
  maxDurationMs: number
}

export interface ReportSummary {
  totalRecords: number
  totalRuns: number
  successCount: number
  failedCount: number
  totalDurationMs: number
  avgDurationMs: number
  minDurationMs: number
  maxDurationMs: number
  metricVersion: number
}

export interface ReportPagination {
  page: number
  pageSize: number
  total: number
  totalPages: number
}

export interface ExecutionReport {
  filters: {
    startTime: string | null
    endTime: string | null
    taskId: string | null
    status: StageStatus | null
    page: number
    pageSize: number
  }
  pagination: ReportPagination
  summary: ReportSummary
  stages: StageSummary[]
  items: ExecutionRecord[]
  taskOptions: TaskOption[]
}
