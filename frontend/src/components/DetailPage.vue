<template>
  <div class="detail-page">
    <ReportFilterBar />
    <div class="content" v-loading="store.reportLoading">
      <div v-if="store.reportError" class="error">{{ store.reportError }}</div>
      <template v-else-if="store.report">
        <div class="detail-header">
          <div>
            <h3>执行明细</h3>
            <p>
              当前口径共 <strong>{{ store.report.pagination.total }}</strong> 条，
              与报表总记录数一致；列表耗时直接读取入库快照，不按当前时间重新计算
            </p>
          </div>
          <div v-if="store.filters.taskId" class="active-filter">
            <span>环节：{{ selectedStageName || store.filters.taskId }}</span>
            <el-button link type="primary" @click="store.updateFilters({ taskId: '', page: 1 })">清除环节筛选</el-button>
          </div>
        </div>

        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>执行ID</th>
                <th>工作流</th>
                <th>环节</th>
                <th>状态</th>
                <th>尝试次数</th>
                <th>开始时间</th>
                <th>结束时间</th>
                <th>耗时</th>
                <th>口径</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in store.report.items" :key="item.id">
                <td><code>#{{ item.runId }}-{{ item.id }}</code></td>
                <td>{{ item.workflowName }} #{{ item.workflowId }}</td>
                <td>{{ item.taskName }} <code>{{ item.taskId }}</code></td>
                <td :class="item.status === 'SUCCESS' ? 'success-text' : 'failed-text'">
                  {{ statusLabel(item.status) }}
                </td>
                <td>{{ item.attempts }}</td>
                <td>{{ formatTime(item.startedAt) }}</td>
                <td>{{ formatTime(item.finishedAt) }}</td>
                <td>{{ formatDuration(item.durationMs) }}</td>
                <td>v{{ item.metricVersion }}</td>
              </tr>
              <tr v-if="!store.report.items.length">
                <td colspan="9" class="empty">当前条件下暂无明细记录</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="pager">
          <el-pagination
            background
            layout="total, sizes, prev, pager, next"
            :total="store.report.pagination.total"
            :page-size="store.report.pagination.pageSize"
            :current-page="store.filters.page"
            :page-sizes="[20, 50, 100]"
            @current-change="onPageChange"
            @size-change="onSizeChange"
          />
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import ReportFilterBar from './ReportFilterBar.vue'
import { useDAGStore } from '@/store/dag'
import { formatDuration, formatTime, statusLabel } from '@/utils/execution'

const store = useDAGStore()
const selectedStageName = computed(() =>
  store.report?.stages.find(stage => stage.taskId === store.filters.taskId)?.taskName
)

function onPageChange(page: number) {
  store.updateFilters({ page })
}

function onSizeChange(pageSize: number) {
  store.updateFilters({ pageSize, page: 1 })
}
</script>

<style scoped>
.detail-page { height: 100%; display: flex; flex-direction: column; background: #0f0f23; }
.content { flex: 1; overflow: auto; padding: 16px; }
.error { padding: 24px; color: #f87171; background: #ef444410; border: 1px solid #ef444444; border-radius: 8px; }
.detail-header { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 12px; }
.detail-header h3 { color: #bb86fc; font-size: 16px; margin-bottom: 4px; }
.detail-header p { color: #8a90b3; font-size: 12px; }
.detail-header strong { color: #e0e0e0; font-size: 14px; }
.active-filter { display: flex; align-items: center; gap: 8px; color: #a0a6c8; font-size: 12px; background: #1a1a2e; border: 1px solid #2a2a4a; border-radius: 999px; padding: 6px 10px; white-space: nowrap; }
.table-wrap { background: #1a1a2e; border: 1px solid #2a2a4a; border-radius: 8px; overflow: auto; }
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th, td { padding: 10px 12px; border-top: 1px solid #2a2a4a; text-align: left; white-space: nowrap; }
th { background: #15152a; color: #a0a6c8; font-weight: 600; position: sticky; top: 0; }
code { color: #8a90b3; font-size: 11px; }
.success-text { color: #38a169; }
.failed-text { color: #ef4444; }
.empty { text-align: center; color: #4a5568; padding: 32px !important; }
.pager { display: flex; justify-content: flex-end; margin-top: 14px; }
</style>
