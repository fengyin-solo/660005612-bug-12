import type { PageView, ReportFilters, StageStatus } from '@/types'

export const FILTER_STORAGE_KEY = 'dag-execution-filters'

export const defaultFilters = (): ReportFilters => ({
  startTime: '',
  endTime: '',
  taskId: '',
  status: '',
  page: 1,
  pageSize: 20,
})

function cleanStatus(value: string | null): StageStatus {
  return value === 'SUCCESS' || value === 'FAILED' ? value : ''
}

function cleanPositive(value: string | null, fallback: number): number {
  const n = Number(value)
  return Number.isInteger(n) && n > 0 ? n : fallback
}

export function normalizeFilters(raw: Partial<Record<keyof ReportFilters, unknown>> = {}): ReportFilters {
  const normalized: ReportFilters = {
    startTime: typeof raw.startTime === 'string' ? raw.startTime : '',
    endTime: typeof raw.endTime === 'string' ? raw.endTime : '',
    taskId: typeof raw.taskId === 'string' ? raw.taskId : '',
    status: cleanStatus(typeof raw.status === 'string' ? raw.status : ''),
    page: cleanPositive(raw.page == null ? '' : String(raw.page), 1),
    pageSize: Math.min(100, cleanPositive(raw.pageSize == null ? '' : String(raw.pageSize), 20)),
  }
  return normalized
}

function readStoredFilters(): ReportFilters {
  try {
    const raw = localStorage.getItem(FILTER_STORAGE_KEY)
    return raw ? normalizeFilters(JSON.parse(raw)) : defaultFilters()
  } catch {
    return defaultFilters()
  }
}

export function parseLocation(): { view: PageView; filters: ReportFilters } {
  const hash = window.location.hash.replace(/^#/, '')
  const [path, query = ''] = hash.split('?')
  const segment = path.replace(/^\//, '')
  const view: PageView = segment === 'report' || segment === 'detail' ? segment : 'workflow'
  const params = new URLSearchParams(query)

  const fromHash = Array.from(params.keys()).length > 0
  const filters = fromHash
    ? normalizeFilters({
        startTime: params.get('startTime') ?? '',
        endTime: params.get('endTime') ?? '',
        taskId: params.get('taskId') ?? '',
        status: params.get('status') ?? '',
        page: params.get('page') ?? '1',
        pageSize: params.get('pageSize') ?? '20',
      })
    : readStoredFilters()

  return { view, filters }
}

export function buildHash(view: PageView, filters: ReportFilters): string {
  const params = new URLSearchParams()
  if (filters.startTime) params.set('startTime', filters.startTime)
  if (filters.endTime) params.set('endTime', filters.endTime)
  if (filters.taskId) params.set('taskId', filters.taskId)
  if (filters.status) params.set('status', filters.status)
  if (filters.page > 1) params.set('page', String(filters.page))
  if (filters.pageSize !== 20) params.set('pageSize', String(filters.pageSize))
  const query = params.toString()
  return `#/${view}${query ? `?${query}` : ''}`
}

export function writeLocation(view: PageView, filters: ReportFilters, replace = false): void {
  const hash = buildHash(view, filters)
  localStorage.setItem(FILTER_STORAGE_KEY, JSON.stringify(filters))
  if (replace) {
    window.history.replaceState(null, '', hash)
  } else if (window.location.hash !== hash) {
    window.location.hash = hash
  }
}

export function filterKey(filters: ReportFilters): string {
  return JSON.stringify([
    filters.startTime,
    filters.endTime,
    filters.taskId,
    filters.status,
    filters.page,
    filters.pageSize,
  ])
}

export function formatDuration(ms: number): string {
  if (!Number.isFinite(ms) || ms < 0) return '-'
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(3).replace(/0+$/, '').replace(/\.$/, '')}s`
}

export function formatTime(value: string | null | undefined): string {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

export function statusLabel(status: string): string {
  return status === 'SUCCESS' ? '成功' : status === 'FAILED' ? '失败' : status
}
