<template>
  <div class="page">
    <FilterBar />

    <div class="check-bar" v-loading="loading">
      <span>当前条件：明细 <b>{{ items.length }}</b> 条，报表 <b>{{ reportCount }}</b> 条</span>
      <el-tag v-if="checked" :type="items.length === reportCount ? 'success' : 'danger'" size="small">
        {{ items.length === reportCount ? '✓ 两处一致' : '✗ 不一致' }}
      </el-tag>
      <el-button text size="small" type="primary" @click="gotoReport">← 返回报表</el-button>
    </div>

    <el-table :data="items" size="small" stripe v-loading="loading" max-height="calc(100vh - 200px)">
      <el-table-column prop="id" label="#执行ID" width="90" />
      <el-table-column prop="name" label="工作流" min-width="120" />
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.status === 'SUCCESS' ? 'success' : 'danger'" size="small">
            {{ STATUS_LABEL[row.status] || row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="开始时间" width="180">
        <template #default="{ row }">{{ fmtTime(row.started_at) }}</template>
      </el-table-column>
      <el-table-column label="总耗时" width="100">
        <template #default="{ row }">{{ fmtDuration(row.duration) }}</template>
      </el-table-column>
      <el-table-column label="执行环节数" width="100" prop="task_count" />
      <el-table-column label="环节耗时合计" width="120">
        <template #default="{ row }">{{ fmtDuration(row.task_duration_sum) }}</template>
      </el-table-column>
      <el-table-column prop="workers" label="Workers" width="90" />
      <el-table-column prop="strategy" label="策略" width="100" />
      <el-table-column label="操作" width="110" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="openRun(row.id)">查看执行明细</el-button>
        </template>
      </el-table-column>
      <template #empty>
        <span class="empty">该时间范围内没有执行记录</span>
      </template>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import FilterBar from '@/components/FilterBar.vue'
import { useUrlFilter } from '@/composables/useFilter'
import { fetchRuns, fetchReport } from '@/api'
import { fmtDuration, fmtTime, STATUS_LABEL } from '@/format'
import { push, filterToQuery } from '@/router'
import type { RunItem } from '@/types'

const { filter } = useUrlFilter()
const items = ref<RunItem[]>([])
const reportCount = ref(0)
const checked = ref(false)
const loading = ref(false)

async function load() {
  loading.value = true
  checked.value = false
  try {
    // Same filter object -> same params -> backend shares one WHERE clause.
    const [rows, rep] = await Promise.all([fetchRuns(filter.value), fetchReport(filter.value)])
    items.value = rows
    reportCount.value = rep.runCount
    checked.value = true
  } finally {
    loading.value = false
  }
}

function openRun(id: number) {
  // Filter rides along, so the detail page can return to THIS exact condition.
  push(`/run/${id}`, filterToQuery(filter.value))
}

function gotoReport() {
  push('/report', filterToQuery(filter.value))
}

watch(filter, load, { immediate: true, deep: true })
</script>

<style scoped>
.page { padding: 16px 20px; height: 100%; overflow-y: auto }
.check-bar { display: flex; gap: 10px; align-items: center; margin-bottom: 10px; color: #bbb; font-size: 13px }
.empty { color: #667 }
</style>
