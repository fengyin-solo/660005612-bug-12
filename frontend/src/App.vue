<template>
  <div class="app-root">
    <header class="top-bar">
      <h1>🔀 分布式任务工作流DAG编排与执行引擎</h1>
      <nav class="nav-tabs">
        <button :class="{ active: store.currentView === 'workflow' }" @click="store.navigate('workflow')">执行监控</button>
        <button :class="{ active: store.currentView === 'report' }" @click="store.navigate('report')">报表</button>
        <button :class="{ active: store.currentView === 'detail' }" @click="store.navigate('detail')">明细</button>
      </nav>
      <template v-if="store.currentView === 'workflow'">
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
      </template>
    </header>

    <ReportPage v-if="store.currentView === 'report'" />
    <DetailPage v-else-if="store.currentView === 'detail'" />
    <div v-else class="main-grid">
      <div class="dag-area">
        <DAGCanvas />
      </div>
      <div class="side-area">
        <LogPanel />
        <CircuitBreakerPanel />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import DAGCanvas from './components/DAGCanvas.vue'
import LogPanel from './components/LogPanel.vue'
import CircuitBreakerPanel from './components/CircuitBreakerPanel.vue'
import ReportPage from './components/ReportPage.vue'
import DetailPage from './components/DetailPage.vue'
import { useDAGStore } from './store/dag'

const store = useDAGStore()
const wfName = ref('data-pipeline')
function create() { store.createWorkflow(wfName.value) }
function run() { store.run() }
onMounted(() => store.connectWS())
onUnmounted(() => store.disconnectWS())
</script>

<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,sans-serif;background:#0c0c1d;color:#e0e0e0}
.app-root{height:100vh;display:flex;flex-direction:column}
.top-bar{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:10px 20px;background:#1a1a2e;border-bottom:1px solid #2a2a4a}
.top-bar h1{font-size:1rem;color:#bb86fc;white-space:nowrap}
.nav-tabs{display:flex;gap:4px;background:#101024;border:1px solid #2a2a4a;border-radius:8px;padding:3px}
.nav-tabs button{border:0;background:transparent;color:#8a90b3;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px}
.nav-tabs button.active{background:#bb86fc;color:#0f0f23;font-weight:700}
.tools{display:flex;gap:6px;align-items:center}
.ws-dot{width:8px;height:8px;border-radius:50%;background:#ef4444}.ws-dot.on{background:#22c55e}
.main-grid{display:grid;grid-template-columns:1fr 320px;flex:1;overflow:hidden}
.dag-area{background:#0f0f23;position:relative;overflow:hidden}
.side-area{display:flex;flex-direction:column;gap:8px;padding:8px;overflow-y:auto;background:#14142b}
</style>
