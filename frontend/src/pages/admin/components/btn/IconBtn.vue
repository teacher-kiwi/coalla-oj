<template>
  <div class="icon-btn-wrapper">
    <el-tooltip effect="dark" :content="name" placement="top">
      <el-button plain size="small">
        <el-icon><component :is="icon" /></el-icon>
      </el-button>
    </el-tooltip>
  </div>
</template>

<script setup>
defineProps({
  name: { type: String, required: true },
  icon: { type: [String, Object], required: true }
})
</script>

<style scoped>
.icon-btn-wrapper {
  display: inline-block;
}
</style>
