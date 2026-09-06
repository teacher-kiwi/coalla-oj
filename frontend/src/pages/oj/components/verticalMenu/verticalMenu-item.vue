<template>
  <li @click.stop="handleClick" :class="{ disabled: disabled }">
    <slot></slot>
  </li>
</template>

<script setup>
import { inject } from 'vue'

const props = defineProps({
  route: { type: [String, Object], default: null },
  disabled: { type: Boolean, default: false }
})

const onClick = inject('verticalMenuOnClick', null)

function handleClick () {
  if (props.route && onClick) {
    onClick(props.route)
  }
}
</script>

<style scoped lang="less">
  .disabled {
    opacity: 1;
    pointer-events: none;
    color: #ccc;
    &:hover {
      border-left: none;
      color: #ccc;
      background: #fff;
    }
  }

  li {
    border-bottom: 1px dashed #e9eaec;
    color: #495060;
    // 아이콘과 글자를 가운데끼리 맞춘다(기준선 정렬이면 아이콘만 뜬다)
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 15px 20px;
    cursor: pointer;
    &:hover {
      background: #f8f8f9;
      border-left: 2px solid #5cadff;
      color: #2d8cf0;
    }
    &:last-child {
      border-bottom: none;
    }
  }
</style>
