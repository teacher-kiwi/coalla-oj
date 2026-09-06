<template>
  <el-tag v-if="state" :type="state.type" size="small" effect="plain">{{ state.label }}</el-tag>
</template>

<script setup>
import { computed } from 'vue'
import { SCOPE_TAG } from '@/utils/constants'

// 학급 안에서만 쓰는 것인지 밖에 공개된 것인지를 보여주는 표. 교사 문제 목록,
// 문제집, 대회 목록에 모두 나와 이름과 색이 갈리기 쉬워 한 군데로 모았다.
// 테두리만 있는 effect="plain" 은 DifficultyTag 와 같아 표 안에서 함께 보기 좋다.
const props = defineProps({
  // 'public' | 'pending' | 'private'(문제) 또는 'class'(대회)
  value: { type: String, default: '' }
})

const state = computed(() => SCOPE_TAG[props.value] || null)
</script>
