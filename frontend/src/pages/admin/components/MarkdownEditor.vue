<template>
  <MdEditor
    v-model="text"
    :editor-id="editorId"
    :language="MD_LANGUAGE"
    :toolbars-exclude="TOOLBARS_EXCLUDE"
    :footers="[]"
    style="height: 400px"
  />
</template>

<script setup>
import { computed, useId } from 'vue'
import { MdEditor } from 'md-editor-v3'
import 'md-editor-v3/lib/style.css'
import { MD_LANGUAGE } from '@/plugins/markdown'

// 저장 포맷이 마크다운이라 편집기가 다루는 값이 곧 저장값이다.
// (예전에는 HTML 로 저장해서, 편집기가 렌더한 HTML 을 부모에게 올려보내고
//  되돌아온 HTML 을 다시 마크다운 소스인 척 넣었다. 그 왕복 때문에 편집창에
//  <p> 태그가 그대로 쌓여 보였다.)
const TOOLBARS_EXCLUDE = ['github']

const props = defineProps({
  modelValue: { type: String, default: '' }
})

const emit = defineEmits(['update:modelValue'])

// 한 화면에 편집기가 여럿이다(설명·입력 설명·출력 설명·힌트).
// editorId 는 내부 이벤트 버스의 키이자 DOM id 라서 기본값을 그대로 쓰면 서로 간섭한다.
const editorId = `md-${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`

const text = computed({
  get: () => props.modelValue || '',
  set: (value) => emit('update:modelValue', value)
})
</script>
