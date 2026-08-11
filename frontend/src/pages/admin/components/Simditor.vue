<template>
  <MdEditor
    v-model="editorText"
    :language="mdEditorLang"
    :toolbars-exclude="['github']"
    :preview="false"
    :footers="[]"
    style="height: 400px"
    @on-html-changed="onHtmlChanged"
  />
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { MdEditor } from 'md-editor-v3'
import 'md-editor-v3/lib/style.css'

const { locale } = useI18n()

const mdEditorLang = computed(() => {
  if (locale.value.startsWith('zh')) return 'zh-CN'
  return 'en-US'
})

// 저장/표시 포맷은 HTML이다. 문제 설명 등은 OJ 화면에서 v-html 로 렌더되고,
// DB 의 기존 데이터도 모두 HTML 이므로 이 컴포넌트는 HTML 을 주고받는다.
// 편집기 자체는 마크다운으로 입력받되(markdown-it 의 html:true 로 기존 HTML 은 그대로 통과),
// 부모에게는 렌더된 HTML 을 넘긴다.
const props = defineProps({
  modelValue: { type: String, default: '' },
  toolbar: { type: Array, default: () => [] }
})

const emit = defineEmits(['update:modelValue', 'change'])

const editorText = ref(props.modelValue)
// 우리가 방금 올려보낸 HTML 이 prop 으로 되돌아온 것인지 구분하기 위한 값.
// 이게 없으면 편집 중 입력이 매번 렌더 결과로 덮어써진다.
let lastEmittedHtml = props.modelValue

function onHtmlChanged (html) {
  if (html === props.modelValue) return
  lastEmittedHtml = html
  emit('update:modelValue', html)
  emit('change', html)
}

watch(() => props.modelValue, (val) => {
  // 자기 자신이 올려보낸 값의 반향이면 무시하고, 외부에서 새로 채워준 경우에만 반영한다.
  if (val === lastEmittedHtml) return
  lastEmittedHtml = val
  editorText.value = val || ''
})
</script>
