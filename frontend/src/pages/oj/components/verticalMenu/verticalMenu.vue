<template>
  <el-card :body-style="{ padding: 0 }" shadow="never">
    <ul class="menu-list">
      <slot></slot>
    </ul>
  </el-card>
</template>

<script setup>
import { provide } from 'vue'

const emit = defineEmits(['on-click'])

provide('verticalMenuOnClick', (route) => {
  emit('on-click', route)
})
</script>

<style scoped>
.menu-list {
  margin: 0;
  padding: 0;
}
</style>
