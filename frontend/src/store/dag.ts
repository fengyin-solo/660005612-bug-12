import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import axios from 'axios'
import type { DAGWorkflow, ExecutionInfo, ExecutionReport, PageView, ReportFilters } from '@/types'
import {
  buildHash,
  defaultFilters,
  filterKey,
  normalizeFilters,
  parseLocation,
  writeLocation,
} from '@/utils/execution'

export const useDAGStore = defineStore('dag', () => {
  const loading = ref(false)
  const workflow = ref<DAGWorkflow | null>(null)
  const execution = ref<ExecutionInfo | null>(null)
  const wsConnected = ref(false)
  const workers = ref(3)
  const strategy = ref('fifo')

  const initial = parseLocation()
  const currentView = ref<PageView>(initial.view)
  const filters = ref<ReportFilters>(initial.filters)
  const report = ref<ExecutionReport | null>(null)
  const reportLoading = ref(false)
  const reportError = ref('')
  const activeFilterKey = ref('')
  let ws: WebSocket | null = null
  let reportRequestId = 0

  const activeFilterSignature = computed(() => filterKey(filters.value))

  function connectWS() {
    ws = new WebSocket(`ws://${location.hostname}:8000/ws`)
    ws.onopen = () => { wsConnected.value = true }
    ws.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data)
        execution.value = d
      } catch {
        // Keep the last valid execution state if a malformed frame arrives.
      }
    }
    ws.onclose = () => { wsConnected.value = false }
    window.addEventListener('hashchange', syncFromLocation)
    void loadReport()
  }

  function syncFromLocation() {
    const next = parseLocation()
    const keyChanged = filterKey(next.filters) !== activeFilterSignature.value
    currentView.value = next.view
    filters.value = next.filters
    if (keyChanged) {
      void loadReport()
    }
  }

  function persistHash(view: PageView, nextFilters: ReportFilters, replace = false) {
    writeLocation(view, nextFilters, replace)
    currentView.value = view
    filters.value = nextFilters
    if (replace) {
      void loadReport()
      return
    }
    if (buildHash(view, nextFilters) === window.location.hash) {
      void loadReport()
    }
    // A changed hash triggers syncFromLocation, which owns the resulting request.
  }

  function navigate(view: PageView) {
    if (view === currentView.value) return
    persistHash(view, filters.value)
  }

  function updateFilters(patch: Partial<ReportFilters>) {
    const next = normalizeFilters({ ...filters.value, ...patch })
    if (patch.taskId !== undefined || patch.startTime !== undefined ||
        patch.endTime !== undefined || patch.status !== undefined) {
      next.page = 1
    }
    persistHash(currentView.value, next)
  }

  function resetFilters() {
    persistHash(currentView.value, defaultFilters())
  }

  function selectStage(taskId: string) {
    const next = normalizeFilters({ ...filters.value, taskId, page: 1 })
    persistHash('detail', next)
  }

  async function loadReport(force = false) {
    if (currentView.value === 'workflow') return
    const key = activeFilterSignature.value
    if (!force && report.value && key === activeFilterKey.value) return

    const requestId = ++reportRequestId
    reportLoading.value = true
    reportError.value = ''
    activeFilterKey.value = key
    try {
      const { data } = await axios.get<ExecutionReport | { error: string }>('/api/execution-report', {
        params: {
          startTime: filters.value.startTime || undefined,
          endTime: filters.value.endTime || undefined,
          taskId: filters.value.taskId || undefined,
          status: filters.value.status || undefined,
          page: filters.value.page,
          pageSize: filters.value.pageSize,
        },
      })
      if (requestId !== reportRequestId) return
      if ('error' in data) {
        reportError.value = data.error
        report.value = null
      } else {
        report.value = data
      }
    } catch (err) {
      if (requestId !== reportRequestId) return
      report.value = null
      reportError.value = axios.isAxiosError(err) && err.response?.data?.detail
        ? String(err.response.data.detail)
        : '报表数据加载失败'
    } finally {
      if (requestId === reportRequestId) reportLoading.value = false
    }
  }

  async function createWorkflow(name: string) {
    loading.value = true
    try {
      const { data } = await axios.post('/api/workflow', { name })
      workflow.value = data
    } finally {
      loading.value = false
    }
  }

  async function run() {
    if (!workflow.value) return
    loading.value = true
    try {
      const { data } = await axios.post('/api/run', {
        workflowId: workflow.value.id,
        workers: workers.value,
        strategy: strategy.value,
      })
      execution.value = data
    } finally {
      loading.value = false
    }
  }

  function disconnectWS() {
    window.removeEventListener('hashchange', syncFromLocation)
    ws?.close()
    ws = null
  }

  return {
    loading,
    workflow,
    execution,
    wsConnected,
    workers,
    strategy,
    currentView,
    filters,
    report,
    reportLoading,
    reportError,
    connectWS,
    disconnectWS,
    navigate,
    updateFilters,
    resetFilters,
    selectStage,
    loadReport,
    createWorkflow,
    run,
  }
})
