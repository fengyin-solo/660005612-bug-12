<template>
  <div class="page">
    <FilterBar />

    <div v-loading="loading">
      <div class="cards">
        <div class="card">
          <div class="card-label">执行条数（与明细列表一致）</div>
          <div class="card-value">{{ report?.runCount ?? 0 }}</div>
        </div>
        <div class="card">
          <div class="card-label">总耗时</div>
          <div class="card-value">{{ fmtDuration(report?.totalDuration ?? 0) }}</div>
        </div>
        <div class="card">
          <div class="card-label">平均耗时</div>
          <div class="card-value">{{ fmtDuration(report?.avgDuration ?? 0) }}</div>
        </div>
        <div class="card cross">
          <div class="card-label">口径自检</div>
          <div class="card-value" :class="{ ok: checked, bad: checked && crossCount !== listCount }">
            <template v-if="!checked">核对中…</template>
            <template v-else-if="crossCount === listCount">✓ 报表 {{ crossCount }} 条 = 明细 {{ listCount }} 条</template>
            <template v-else>✗ 不一致：{{ crossCount }} ≠ {{ listCount }}</template>
          </div>
        </div>
      </div>

      <div class="grid-2">
        <el-card shadow="never">
          <template #header><span class="sec">按执行状态</span></template>
          <el-table :data="report?.byStatus ?? []" size="small">
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.status === 'SUCCESS' ? 'success' : 'danger'" size="small">
                  {{ STATUS_LABEL[row.status] || row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="count" label="条数" width="90" />
            <el-table-column label="耗时合计">
              <template #default="{ row }">{{ fmtDuration(row.duration) }}</template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-card shadow="never">
          <template #header>
            <span class="sec">按环节（耗时 = 首次开始 → 最终结束，含重试）</span>
          </template>
          <el-table :data="report?.tasks ?? []" size="small" max-height="320">
            <el-table-column prop="task_name" label="环节" min-width="100" />
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="stageTagType(row.status)" size="small">
                  {{ STATUS_LABEL[row.status] || (row.status === 'SKIPPED' ? '未执行' : row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="count" label="执行次数" width="80" />
            <el-table-column label="总耗时" width="100">
              <template #default="{ row }">
                {{ row.status === 'SKIPPED' ? '未执行' : fmtDuration(row.duration) }}
              </template>
            </el-table-column>
            <el-table-column label="平均耗时" width="100">
              <template #default="{ row }">
                {{ row.status === 'SKIPPED' ? '未执行' : fmtDuration(row.avg_duration) }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </div>

      <div class="actions">
        <el-button type="primary" size="small" @click="gotoDetail">
          查看该条件下的明细列表（{{ listCount }} 条）→
        </el-button>
        <span class="hint">跳转携带当前筛选条件，不会被清空</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import FilterBar from '@/components/FilterBar.vue'
import { useUrlFilter } from '@/composables/useFilter'
import { fetchReport, fetchRuns } from '@/api'
import { fmtDuration, STATUS_LABEL } from '@/format'
import { push, filterToQuery } from '@/router'
import type { ReportData } from '@/types'

const { filter } = useUrlFilter()
const report = ref<ReportData | null>(null)
const loading = ref(false)
const listCount = ref(0)
const checked = ref(false)
const crossCount = ref(0)

function stageTagType(status: string) {
  if (status === 'SUCCESS') return 'success'
  if (status === 'SKIPPED') return 'info'
  return 'danger'
}

async function load() {
  loading.value = true
  checked.value = false
  try {
    // Fetch through both endpoints with the SAME filter: not only do they share
    // one WHERE clause on the backend, the UI visibly verifies they agree.
    const [rep, rows] = await Promise.all([fetchReport(filter.value), fetchRuns(filter.value)])
    report.value = rep
    listCount.value = rows.length
    crossCount.value = rep.runCount
    checked.value = true
  } finally {
    loading.value = false
  }
}

function gotoDetail() {
  push('/detail', filterToQuery(filter.value))
}

watch(filter, load, { immediate: true, deep: true })
</script>

<style scoped>
.page { padding: 16px 20px; height: 100%; overflow-y: auto }
.cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 14px }
.card { background: #1a1a2e; border: 1px solid #2a2a4a; border-radius: 8px; padding: 12px 14px }
.card-label { color: #888; font-size: 12px; margin-bottom: 6px }
.card-value { font-size: 22px; font-weight: 700; color: #e0e0e0 }
.card-value.ok { font-size: 14px; color: #38a169 }
.card-value.bad { font-size: 14px; color: #e53e3e }
.grid-2 { display: grid; grid-template-columns: 1fr 1.4fr; gap: 12px }
.sec { color: #bb86fc; font-size: 13px }
.actions { margin-top: 14px; display: flex; align-items: center; gap: 10px }
.hint { color: #667; font-size: 11px }
</style>
