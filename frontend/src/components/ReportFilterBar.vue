<template>
  <div class="filter-bar">
    <el-date-picker
      v-model="dateRange"
      type="daterange"
      unlink-panels
      value-format="YYYY-MM-DD"
      range-separator="至"
      start-placeholder="开始日期"
      end-placeholder="结束日期"
      size="small"
      style="width: 260px"
    />
    <el-select
      :model-value="store.filters.taskId"
      clearable
      filterable
      placeholder="全部环节"
      size="small"
      style="width: 170px"
      @update:model-value="(v: string) => store.updateFilters({ taskId: v || '', page: 1 })"
    >
      <el-option
        v-for="option in store.report?.taskOptions || []"
        :key="option.taskId"
        :label="option.taskName"
        :value="option.taskId"
      />
    </el-select>
    <el-select
      :model-value="store.filters.status || undefined"
      clearable
      placeholder="全部状态"
      size="small"
      style="width: 120px"
      @update:model-value="(v: string) => store.updateFilters({ status: (v || '') as StageStatus, page: 1 })"
    >
      <el-option label="成功" value="SUCCESS" />
      <el-option label="失败" value="FAILED" />
    </el-select>
    <el-button size="small" @click="store.loadReport(true)" :loading="store.reportLoading">刷新</el-button>
    <el-button size="small" @click="store.resetFilters">重置</el-button>
    <span class="filter-hint">当前条件会写入地址栏，返回与刷新后仍保持一致</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useDAGStore } from '@/store/dag'
import type { StageStatus } from '@/types'

const store = useDAGStore()
const dateRange = computed<[string, string] | null>({
  get() {
    const { startTime, endTime } = store.filters
    return startTime && endTime ? [startTime, endTime] : null
  },
  set(value) {
    store.updateFilters({
      startTime: value?.[0] || '',
      endTime: value?.[1] || '',
      page: 1,
    })
  },
})
</script>

<style scoped>
.filter-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding: 12px 16px;
  background: #1a1a2e;
  border-bottom: 1px solid #2a2a4a;
}
.filter-hint {
  color: #7c83a8;
  font-size: 12px;
}
</style>
