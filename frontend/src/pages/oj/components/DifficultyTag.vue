<template>
  <el-tag :style="tagStyle" size="small" effect="plain">{{ label }}</el-tag>
</template>

<script setup>
import { computed } from 'vue'
import { DIFFICULTY_LABEL, DIFFICULTY_COLOR } from '@/utils/constants'

// 난이도 표시는 문제 목록·문제집 등 여러 화면에 나온다.
// 색과 이름을 한 군데서 정하려고 작은 컴포넌트로 뺐다.
const props = defineProps({
  value: { type: String, default: '' }
})

const label = computed(() => DIFFICULTY_LABEL[props.value] || '-')

const tagStyle = computed(() => {
  const color = DIFFICULTY_COLOR[props.value]
  if (!color) return {}
  // 배경은 연하게 깔고 글자와 테두리에 색을 준다(초등 화면이라 눈이 덜 피로하게)
  return { backgroundColor: `${color}1a`, borderColor: `${color}66`, color }
})
</script>
