<template>
  <div class="app-root">
    <header class="top-bar">
      <h1>🔀 分布式任务工作流DAG编排与执行引擎</h1>
      <div class="tools">
        <el-input v-model="wfName" placeholder="工作流名称" size="small" style="width:160px"/>
        <el-button size="small" @click="create" :loading="store.loading">创建DAG</el-button>
        <el-select v-model="store.workers" size="small" style="width:100px">
          <el-option :value="1" label="1 Worker"/><el-option :value="3" label="3 Workers"/><el-option :value="5" label="5 Workers"/>
        </el-select>
        <el-select v-model="store.strategy" size="small" style="width:100px">
          <el-option value="fifo" label="FIFO"/><el-option value="priority" label="优先级"/><el-option value="max_concurrent" label="最大并发"/>
        </el-select>
        <el-button type="success" size="small" @click="run" :disabled="!store.workflow" :loading="store.loading">▶ 执行</el-button>
        <span class="ws-dot" :class="{on:store.wsConnected}"></span>
      </div>
    </header>
    <nav class="tab-bar">
      <button class="tab" :class="{active: isLive}" @click="go('/')">实时监控</button>
      <button class="tab" :class="{active: isReport}" @click="go('/report')">执行报表</button>
      <button class="tab" :class="{active: isDetail}" @click="go('/detail')">明细列表</button>
    </nav>

    <LiveView v-if="isLive" class="tab-body" />
    <ReportPage v-else-if="isReport" class="tab-body" />
    <DetailPage v-else-if="isDetail" class="tab-body" />
    <RunDetailPage v-else-if="isRun" class="tab-body" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import ReportPage from './pages/ReportPage.vue'
import DetailPage from './pages/DetailPage.vue'
import RunDetailPage from './pages/RunDetailPage.vue'
import LiveView from './pages/LiveView.vue'
import { useDAGStore } from './store/dag'
import { route, push } from './router'

const store = useDAGStore()
const wfName = ref('data-pipeline')
function create() { store.createWorkflow(wfName.value) }
function run() { store.run() }
onMounted(() => store.connectWS())
onUnmounted(() => store.disconnectWS())

const path = computed(() => route.value.path)
const isLive = computed(() => path.value === '/')
const isReport = computed(() => path.value === '/report')
const isDetail = computed(() => path.value === '/detail')
const isRun = computed(() => path.value.startsWith('/run/'))
function go(p: string) {
  // Keep the current time-range filter when switching between report/detail.
  push(p, route.value.query)
}
</script>

<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,sans-serif;background:#0c0c1d;color:#e0e0e0}
.app-root{height:100vh;display:flex;flex-direction:column}
.top-bar{display:flex;justify-content:space-between;align-items:center;padding:10px 20px;background:#1a1a2e;border-bottom:1px solid #2a2a4a}
.top-bar h1{font-size:1rem;color:#bb86fc}
.tools{display:flex;gap:6px;align-items:center}
.ws-dot{width:8px;height:8px;border-radius:50%;background:#ef4444}.ws-dot.on{background:#22c55e}
.tab-bar{display:flex;gap:4px;padding:0 16px;background:#15152a;border-bottom:1px solid #2a2a4a}
.tab{background:none;border:none;color:#8a8ab0;padding:10px 18px;cursor:pointer;font-size:13px;border-bottom:2px solid transparent}
.tab:hover{color:#e0e0e0}
.tab.active{color:#bb86fc;border-bottom-color:#bb86fc}
.tab-body{flex:1;min-height:0;overflow:hidden;display:flex;flex-direction:column}
</style>

<style scoped>
.main-grid{display:grid;grid-template-columns:1fr 320px;flex:1;overflow:hidden}
.dag-area{background:#0f0f23;position:relative;overflow:hidden}
.side-area{display:flex;flex-direction:column;gap:8px;padding:8px;overflow-y:auto;background:#14142b}
</style>
