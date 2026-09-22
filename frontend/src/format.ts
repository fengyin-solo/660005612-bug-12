/** Formatting shared by the report and the detail list — never duplicate these. */

export function fmtDuration(seconds: number): string {
  if (seconds === null || seconds === undefined || Number.isNaN(seconds)) return '—'
  if (seconds >= 60) {
    const m = Math.floor(seconds / 60)
    const s = seconds - m * 60
    return `${m}m${s.toFixed(1)}s`
  }
  return `${seconds.toFixed(2)}s`
}

export function fmtTime(epochSeconds: number): string {
  if (!epochSeconds) return '—'
  const d = new Date(epochSeconds * 1000)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}

export const STATUS_LABEL: Record<string, string> = {
  SUCCESS: '成功', FAILED: '失败', RUNNING: '运行中', PENDING: '等待中',
}
