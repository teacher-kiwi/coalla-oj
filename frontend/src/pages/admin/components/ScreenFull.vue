<template>
  <el-icon class="screenfull" :size="width" :color="color" @click="toggle">
    <FullScreen />
  </el-icon>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { FullScreen } from '@element-plus/icons-vue'

defineProps({
  width: { type: Number, default: 22 },
  height: { type: Number, default: 22 },
  color: { type: String, default: '#5A5E66' }
})

function toggle () {
  const doc = document
  const el = doc.documentElement
  if (!doc.fullscreenElement && !doc.webkitFullscreenElement) {
    if (el.requestFullscreen) el.requestFullscreen()
    else if (el.webkitRequestFullscreen) el.webkitRequestFullscreen()
    else ElMessage.warning("Your browser doesn't support fullscreen")
  } else {
    if (doc.exitFullscreen) doc.exitFullscreen()
    else if (doc.webkitExitFullscreen) doc.webkitExitFullscreen()
  }
}
</script>

<style scoped>
.screenfull {
  display: inline-block;
  cursor: pointer;
  vertical-align: -0.15em;
}
</style>
