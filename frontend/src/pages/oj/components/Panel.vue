<template>
  <el-card :shadow="shadowMode" :body-style="{ padding: padding + 'px' }" class="panel">
    <template #header>
      <div class="panel-header">
        <div class="panel-title">
          <slot name="title"></slot>
        </div>
        <div class="panel-extra">
          <slot name="extra"></slot>
        </div>
      </div>
    </template>
    <div class="panel-body">
      <slot></slot>
    </div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  shadow: { type: Boolean, default: false },
  padding: { type: Number, default: 0 },
  disHover: { type: Boolean, default: false },
  bordered: { type: Boolean, default: true }
})

const shadowMode = computed(() => (props.shadow ? 'always' : 'never'))
</script>

<style lang="less">
  @import (reference) '../../../styles/common.less';

  .panel {
    .panel-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .panel-title {
      .section-title;
      padding: 5px 15px;
    }
    .panel-extra {
      line-height: 40px;
      ul.filter {
        > li {
          display: inline-block;
          padding: 0 10px;
        }
      }
    }
    .panel-body {
      word-break: break-all;
      word-wrap: break-word;
    }
  }
</style>
