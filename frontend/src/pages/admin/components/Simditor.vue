<template>
  <MdEditor
    v-model="editorText"
    :editor-id="editorId"
    language="en-US"
    :toolbars-exclude="TOOLBARS_EXCLUDE"
    :footers="[]"
    style="height: 400px"
    @on-html-changed="onHtmlChanged"
  />
</template>

<script setup>
import { ref, useId, watch } from 'vue'
import { MdEditor } from 'md-editor-v3'
import 'md-editor-v3/lib/style.css'

// md-editor-v3 는 zh-CN/en-US 만 내장하고 있어 도구모음 툴팁은 영어로 둔다.
// 저장/표시 포맷은 HTML이다. 문제 설명 등은 OJ 화면에서 v-html 로 렌더되고,
// DB 의 기존 데이터도 모두 HTML 이므로 이 컴포넌트는 HTML 을 주고받는다.
// 편집기 자체는 마크다운으로 입력받되(markdown-it 의 html:true 로 기존 HTML 은 그대로 통과),
// 부모에게는 렌더된 HTML 을 넘긴다.

// 미리보기를 끄면 안 된다. md-editor-v3 는 미리보기 창(ContentPreview)이 마운트될 때만
// 마크다운을 HTML 로 렌더하고 on-html-changed 를 쏜다. 즉 미리보기가 꺼져 있으면
// 부모의 v-model 이 영원히 빈 문자열로 남는다(화면에는 글이 보이는데 저장은 "빈 값"으로
// 거부되는 형태로 드러난다). 그래서 미리보기를 끄는 도구모음 버튼도 함께 뺀다.
const TOOLBARS_EXCLUDE = ['github', 'preview', 'previewOnly', 'htmlPreview']

const props = defineProps({
  modelValue: { type: String, default: '' },
  toolbar: { type: Array, default: () => [] }
})

const emit = defineEmits(['update:modelValue', 'change'])

// 한 화면에 편집기가 여러 개 있다(설명·입력 설명·출력 설명·힌트).
// editorId 는 내부 이벤트 버스의 키이자 DOM id 라서 기본값을 그대로 쓰면 서로 간섭한다.
const editorId = `md-${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`

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
