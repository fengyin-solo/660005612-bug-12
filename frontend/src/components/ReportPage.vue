<template>
  <div class="report-page">
    <ReportFilterBar />
    <div class="content">
      <div v-loading="store.reportLoading" class="report-body">
        <div v-if="store.reportError" class="error">{{ store.reportError }}</div>
        <template v-else-if="store.report">
          <div class="metric-grid">
            <div class="metric-card">
              <span class="metric-label">总记录数</span>
              <strong>{{ summary.totalRecords }}</strong>
            </div>
            <div class="metric-card">
              <span class="metric-label">执行次数</span>
              <strong>{{ summary.totalRuns }}</strong>
            </div>
            <div class="metric-card success">
              <span class="metric-label">成功</span>
              <strong>{{ summary.successCount }}</strong>
            </div>
            <div class="metric-card failed">
              <span class="metric-label">失败</span>
              <strong>{{ summary.failedCount }}</strong>
            </div>
            <div class="metric-card">
              <span class="metric-label">总耗时</span>
              <strong>{{ formatDuration(summary.totalDurationMs) }}</strong>
            </div>
            <div class="metric-card">
              <span class="metric-label">平均耗时</span>
              <strong>{{ formatDuration(summary.avgDurationMs) }}</strong>
            </div>
            <div class="metric-card wide">
              <span class="metric-label">口径版本</span>
              <strong>v{{ summary.metricVersion }}（仅读取已入库历史）</strong>
            </div>
          </div>

          <section class="table-section">
            <div class="section-title">
              <h3>按环节汇总</h3>
              <span>共 {{ store.report.stages.length }} 个环节，记录数合计 {{ summary.totalRecords }}</span>
            </div>
            <div class="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>环节</th>
                    <th>条数</th>
                    <th>成功</th>
                    <th>失败</th>
                    <th>总耗时</th>
                    <th>平均耗时</th>
                    <th>最小</th>
                    <th>最大</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="stage in store.report.stages" :key="stage.taskId">
                    <td>{{ stage.taskName }} <code>{{ stage.taskId }}</code></td>
                    <td>{{ stage.count }}</td>
                    <td class="success-text">{{ stage.successCount }}</td>
                    <td class="failed-text">{{ stage.failedCount }}</td>
                    <td>{{ formatDuration(stage.totalDurationMs) }}</td>
                    <td>{{ formatDuration(stage.avgDurationMs) }}</td>
                    <td>{{ formatDuration(stage.minDurationMs) }}</td>
                    <td>{{ formatDuration(stage.maxDurationMs) }}</td>
                    <td><el-button link type="primary" @click="store.selectStage(stage.taskId)">查看明细</el-button></td>
                  </tr>
                  <tr v-if="!store.report.stages.length">
                    <td colspan="9" class="empty">当前条件下暂无已完成环节记录</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import ReportFilterBar from './ReportFilterBar.vue'
import { useDAGStore } from '@/store/dag'
import { formatDuration } from '@/utils/execution'

const store = useDAGStore()
const summary = computed(() => store.report?.summary || {
  totalRecords: 0,
  totalRuns: 0,
  successCount: 0,
  failedCount: 0,
  totalDurationMs: 0,
  avgDurationMs: 0,
  minDurationMs: 0,
  maxDurationMs: 0,
  metricVersion: 1,
})
</script>

<style scoped>
.report-page { height: 100%; display: flex; flex-direction: column; background: #0f0f23; }
.content { flex: 1; overflow: auto; padding: 16px; }
.report-body { min-height: 100%; }
.error { padding: 24px; color: #f87171; background: #ef444410; border: 1px solid #ef444444; border-radius: 8px; }
.metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 16px; }
.metric-card { background: #1a1a2e; border: 1px solid #2a2a4a; border-radius: 8px; padding: 14px; display: flex; flex-direction: column; gap: 8px; }
.metric-card.wide { grid-column: span 2; }
.metric-label { color: #8a90b3; font-size: 12px; }
.metric-card strong { color: #e0e0e0; font-size: 20px; }
.metric-card.success strong { color: #38a169; }
.metric-card.failed strong { color: #ef4444; }
.table-section { background: #1a1a2e; border: 1px solid #2a2a4a; border-radius: 8px; overflow: hidden; }
.section-title { display: flex; align-items: baseline; justify-content: space-between; padding: 14px 16px; }
.section-title h3 { color: #bb86fc; font-size: 15px; }
.section-title span { color: #8a90b3; font-size: 12px; }
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th, td { padding: 10px 12px; border-top: 1px solid #2a2a4a; text-align: left; white-space: nowrap; }
th { background: #15152a; color: #a0a6c8; font-weight: 600; }
code { color: #8a90b3; font-size: 11px; }
.success-text { color: #38a169; }
.failed-text { color: #ef4444; }
.empty { text-align: center; color: #4a5568; padding: 32px !important; }
</style>
