<template>
  <div class="accordion">
    <header>
      <h2>{{ title }}</h2>
      <div class="header_right">
        <slot name="header"></slot>
      </div>
    </header>
    <div class="body" v-show="isOpen">
      <slot></slot>
    </div>
    <footer @click="isOpen = !isOpen">
      <el-icon :class="{ rotate: !isOpen }"><CaretTop /></el-icon>
    </footer>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  title: { type: String, required: true }
})

const isOpen = ref(true)
</script>

<style lang="less" scoped>
  .accordion {
    border: 1px solid #eaeefb;
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      min-height: 50px;
      padding: 0 10px;
      h2 {
        font-size: 14px;
        margin: 0;
      }
      .header_right {
        display: flex;
        align-items: center;
        gap: 8px;
      }
    }
    .body {
      background-color: #f9fafc;
      border-top: 1px solid #eaeefb;
      clear: both;
      overflow: hidden;
      padding: 15px 10px;
    }
    footer {
      border-top: 1px solid #eaeefb;
      height: 36px;
      box-sizing: border-box;
      background-color: #fff;
      border-bottom-left-radius: 4px;
      border-bottom-right-radius: 4px;
      text-align: center;
      margin-top: -1px;
      color: #d3dce6;
      cursor: pointer;
      transition: .2s;
      &:hover {
        background-color: #f9fafc;
      }
      .rotate {
        transform: rotate(180deg);
      }
    }
  }
</style>
