import { reactive, computed } from 'vue'
import type { RunFilter } from '@/types'

/**
 * Minimal hash router. Route + filter both live in the URL hash
 * (#/report?start=...&end=...&status=...), so:
 *  - jumping report -> detail -> back never clears the filter,
 *  - a browser refresh restores the exact same condition,
 *  - the link can be copied/bookmarked.
 */

interface RouteState { path: string; query: Record<string, string> }

function parseHash(): RouteState {
  const raw = window.location.hash.replace(/^#/, '') || '/'
  const [path, qs] = raw.split('?')
  const query: Record<string, string> = {}
  if (qs) {
    for (const pair of qs.split('&')) {
      if (!pair) continue
      const [k, v] = pair.split('=')
      query[decodeURIComponent(k)] = decodeURIComponent(v ?? '')
    }
  }
  return { path: path || '/', query }
}

const state = reactive<RouteState>(parseHash())
window.addEventListener('hashchange', () => {
  const next = parseHash()
  state.path = next.path
  state.query = next.query
})

export const route = computed(() => state)

export function push(path: string, query?: Record<string, string | number | undefined>) {
  let hash = '#' + path
  if (query) {
    const parts = Object.entries(query)
      .filter(([, v]) => v !== undefined && v !== '' && v !== null)
      .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
    if (parts.length) hash += '?' + parts.join('&')
  }
  if (window.location.hash === hash) {
    // Same hash still needs a re-read if state was edited programmatically;
    // in practice hashchange covers normal navigation.
    const next = parseHash()
    state.path = next.path
    state.query = next.query
  } else {
    window.location.hash = hash
  }
}

/** Read the shared run filter from a route query (times are epoch SECONDS). */
export function filterFromQuery(query: Record<string, string>): RunFilter {
  const f: RunFilter = {}
  const start = Number(query.start)
  const end = Number(query.end)
  if (Number.isFinite(start) && start > 0) f.start = start
  if (Number.isFinite(end) && end > 0) f.end = end
  if (query.status) f.status = query.status
  return f
}

export function filterToQuery(f: RunFilter): Record<string, number | string | undefined> {
  return { start: f.start ? Math.floor(f.start) : undefined, end: f.end ? Math.floor(f.end) : undefined, status: f.status }
}

/** Merge current filter into a destination link — the condition rides along. */
export function linkWithFilter(path: string, f: RunFilter, extra?: Record<string, string>) {
  return { path, query: { ...filterToQuery(f), ...extra } }
}
