<template>
  <div class="page">
    <div class="head">
      <el-button size="small" @click="back">← 返回明细列表（保留筛选）</el-button>
      <span v-if="data" class="title">
        执行 #{{ data.run.id }} · {{ data.run.name }}
        <el-tag :type="data.run.status === 'SUCCESS' ? 'success' : 'danger'" size="small">
          {{ STATUS_LABEL[data.run.status] || data.run.status }}
        </el-tag>
        <span class="sub">{{ fmtTime(data.run.started_at) }} · 总耗时 {{ fmtDuration(data.run.duration) }}</span>
      </span>
    </div>

    <el-table v-if="data" :data="data.tasks" size="small" stripe>
      <el-table-column prop="seq" label="#" width="60" />
      <el-table-column prop="task_id" label="环节ID" width="140" />
      <el-table-column prop="task_name" label="环节" min-width="120" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="stageTagType(row.status)" size="small">
            {{ STATUS_LABEL[row.status] || (row.status === 'SKIPPED' ? '未执行' : row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="尝试次数" width="90" prop="attempts" />
      <el-table-column label="开始时间" width="180">
        <template #default="{ row }">{{ fmtTime(row.started_at) }}</template>
      </el-table-column>
      <el-table-column label="耗时（含重试）" width="130">
        <template #default="{ row }">
          {{ row.status === 'SKIPPED' ? '未执行' : fmtDuration(row.duration) }}
        </template>
      </el-table-column>
    </el-table>
    <div v-else v-loading="true" style="height:200px"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useUrlFilter } from '@/composables/useFilter'
import { fetchRunDetail } from '@/api'
import { fmtDuration, fmtTime, STATUS_LABEL } from '@/format'
import { route, push, filterToQuery } from '@/router'
import type { RunDetail } from '@/types'

const { filter } = useUrlFilter()
const data = ref<RunDetail | null>(null)

function stageTagType(status: string) {
  if (status === 'SUCCESS') return 'success'
  if (status === 'SKIPPED') return 'info'
  return 'danger'
}

async function load() {
  const id = Number(route.value.path.split('/')[2])
  if (!id) return
  data.value = await fetchRunDetail(id)
}

function back() {
  push('/detail', filterToQuery(filter.value))
}

watch(() => route.value.path, load, { immediate: true })
</script>

<style scoped>
.page { padding: 16px 20px; height: 100%; overflow-y: auto }
.head { display: flex; gap: 14px; align-items: center; margin-bottom: 14px }
.title { font-size: 15px; color: #e0e0e0; display: flex; gap: 8px; align-items: center }
.sub { color: #888; font-size: 12px; font-weight: 400 }
</style>
