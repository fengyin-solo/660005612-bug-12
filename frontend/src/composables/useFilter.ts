import { computed } from 'vue'
import type { RunFilter } from '@/types'
import { route, push, filterFromQuery, filterToQuery } from '@/router'

/**
 * One filter state, bound to the URL hash, used by BOTH the report page and
 * the detail page. Because both pages derive their filter from the exact same
 * query string (and both APIs receive the same params built from it), their
 * numbers cannot drift apart.
 */
export function useUrlFilter() {
  const filter = computed<RunFilter>(() => filterFromQuery(route.value.query))

  function update(patch: Partial<RunFilter>) {
    const next: RunFilter = { ...filter.value, ...patch }
    // Empty values drop out of the URL.
    push(route.value.path, filterToQuery(next))
  }

  function reset() {
    push(route.value.path)
  }

  /** Rolling window ending now (epoch seconds). */
  function setLastDays(days: number) {
    const end = Math.ceil(Date.now() / 1000)
    update({ start: end - days * 86400, end: undefined })
  }

  return { filter, update, reset, setLastDays }
}
