import axios from 'axios'
import type { ReportData, RunDetail, RunFilter, RunItem } from '@/types'

const http = axios.create({ baseURL: '/api' })

/**
 * The report page and the detail list send the SAME params object built by the
 * SAME helper. There is intentionally no second place that constructs these
 * query strings — this is what keeps the two calibers identical.
 */
export function filterParams(f: RunFilter) {
  const p: Record<string, number | string> = {}
  if (f.start) p.start = f.start
  if (f.end) p.end = f.end
  if (f.status) p.status = f.status
  return p
}

export async function fetchRuns(f: RunFilter): Promise<RunItem[]> {
  const { data } = await http.get('/runs', { params: filterParams(f) })
  return data.items
}

export async function fetchReport(f: RunFilter): Promise<ReportData> {
  const { data } = await http.get('/report', { params: filterParams(f) })
  return data
}

export async function fetchRunDetail(id: number): Promise<RunDetail> {
  const { data } = await http.get(`/runs/${id}`)
  return data
}
