<template>
  <MdEditor
    v-model="text"
    :editor-id="editorId"
    :language="MD_LANGUAGE"
    :toolbars-exclude="TOOLBARS_EXCLUDE"
    :on-upload-img="onUploadImg"
    :footers="[]"
    no-mermaid
    no-prettier
    style="height: 400px"
  />
</template>

<script setup>
import { computed, useId } from 'vue'
import { ElMessage } from 'element-plus'
import { MdEditor, config } from 'md-editor-v3'
import 'md-editor-v3/lib/style.css'
import Cropper from 'cropperjs'
import 'cropperjs/dist/cropper.css'
import screenfull from 'screenfull'
import { MD_LANGUAGE } from '@/plugins/markdown'
import { uploadImage } from '@/utils/upload'

// 편집기에서만 쓰는 곁가지 라이브러리. plugins/markdown.js 와 같은 이유로
// CDN 대신 번들에 든 것을 넘긴다. (자르기: 그림 올리기 창의 "잘라서 올리기",
// 전체화면: 도구모음의 전체화면. 둘 다 안 넘기면 화면을 열 때마다 unpkg 를 부른다)
config({
  editorExtensions: {
    cropper: { instance: Cropper },
    screenfull: { instance: screenfull }
  }
})

// 문제 설명·공지에 쓸 일이 없거나, 눌러도 할 일이 없는 것을 뺀다.
// mermaid(순서도 문법)·prettier(마크다운 정렬)는 각각 밖에서 라이브러리를
// 받아와야 하고, save 는 폼의 저장 단추가 따로 있어 눌러도 아무 일이 없다.
const TOOLBARS_EXCLUDE = [
  'github', 'mermaid', 'prettier', 'save', 'previewOnly', 'htmlPreview', 'catalog'
]

const props = defineProps({
  modelValue: { type: String, default: '' }
})

const emit = defineEmits(['update:modelValue'])

// 한 화면에 편집기가 여럿이다(설명·입력 설명·출력 설명·힌트).
// editorId 는 내부 이벤트 버스의 키이자 DOM id 라서 기본값을 그대로 쓰면 서로 간섭한다.
const editorId = `md-${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`

// 저장 포맷이 마크다운이라 편집기가 다루는 값이 곧 저장값이다.
// (예전에는 HTML 로 저장해서, 편집기가 렌더한 HTML 을 부모에게 올려보내고
//  되돌아온 HTML 을 다시 마크다운 소스인 척 넣었다. 그 왕복 때문에 편집창에
//  <p> 태그가 그대로 쌓여 보였다.)
const text = computed({
  get: () => props.modelValue || '',
  set: (value) => emit('update:modelValue', value)
})

// 편집기는 이 훅이 없으면 그림을 올려도 아무 일도 하지 않는다(기본 동작이 없다).
// 올린 주소를 callback 으로 돌려주면 편집기가 본문에 넣는다.
async function onUploadImg (files, callback) {
  const urls = []
  for (const file of files) {
    try {
      urls.push(await uploadImage(file))
    } catch (e) {
      ElMessage.error(e.message || '그림을 올리지 못했습니다')
    }
  }
  callback(urls)
}
</script>
