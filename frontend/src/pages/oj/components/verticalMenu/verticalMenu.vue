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
/* 태블릿 세로(1000px 아래)에서는 오른쪽 칸이 본문 위·아래로 옮겨 가므로 메뉴를 가로로 눕힌다 */
@media (max-width: 1000px) {
  .menu-list {
    display: flex;
    flex-wrap: wrap;
  }
}
</style>
