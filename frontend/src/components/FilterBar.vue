<template>
  <div class="filter-bar">
    <el-date-picker
      :model-value="range"
      type="datetimerange"
      size="small"
      range-separator="至"
      start-placeholder="开始时间"
      end-placeholder="结束时间"
      value-format="x"
      @update:model-value="onRange"
      @clear="update({ start: undefined, end: undefined })"
    />
    <el-select
      :model-value="filter.status || ''"
      size="small"
      placeholder="执行状态"
      clearable
      style="width:120px"
      @update:model-value="(v: string) => update({ status: v || undefined })"
    >
      <el-option value="SUCCESS" label="成功" />
      <el-option value="FAILED" label="失败" />
    </el-select>
    <el-button size="small" @click="setLastDays(1)">近1天</el-button>
    <el-button size="small" @click="setLastDays(7)">近7天</el-button>
    <el-button size="small" @click="setLastDays(30)">近30天</el-button>
    <el-button size="small" @click="reset">清除筛选</el-button>
    <span class="hint">条件保存在地址栏，跳转/刷新均保留</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useUrlFilter } from '@/composables/useFilter'

const { filter, update, reset, setLastDays } = useUrlFilter()

// value-format="x" gives millisecond timestamps as strings; the URL stores seconds.
const range = computed<[string, string] | null>(() =>
  filter.value.start || filter.value.end
    ? [String((filter.value.start ?? 0) * 1000), String((filter.value.end ?? Date.now() / 1000) * 1000)]
    : null
)

function onRange(v: [string | number, string | number] | null) {
  if (!v) {
    update({ start: undefined, end: undefined })
    return
  }
  update({ start: Math.floor(Number(v[0]) / 1000), end: Math.ceil(Number(v[1]) / 1000) })
}
</script>

<style scoped>
.filter-bar { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-bottom: 12px }
.hint { color: #667; font-size: 11px }
</style>
