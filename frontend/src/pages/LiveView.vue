<template>
  <div class="main-grid">
    <div class="dag-area">
      <DAGCanvas />
    </div>
    <div class="side-area">
      <LogPanel />
      <CircuitBreakerPanel />
    </div>
  </div>
</template>

<script setup lang="ts">
import DAGCanvas from '@/components/DAGCanvas.vue'
import LogPanel from '@/components/LogPanel.vue'
import CircuitBreakerPanel from '@/components/CircuitBreakerPanel.vue'
</script>

<style scoped>
.main-grid{display:grid;grid-template-columns:1fr 320px;flex:1;overflow:hidden}
.dag-area{background:#0f0f23;position:relative;overflow:hidden}
.side-area{display:flex;flex-direction:column;gap:8px;padding:8px;overflow-y:auto;background:#14142b}
</style>
