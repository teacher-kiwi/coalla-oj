<template>
  <!-- 저장된 마크다운을 화면에 그리는 유일한 자리.
       편집기와 같은 렌더러를 쓰므로 작성 중 미리보기와 실제 화면이 어긋나지 않는다.
       원시 HTML 은 plugins/markdown.js 에서 꺼둬(html: false) 글자로 이스케이프된다. -->
  <!-- no-mermaid: 순서도 문법은 쓰지 않는다. 켜 두면 화면마다 unpkg 에서
       mermaid 를 받아온다(수식·코드 색은 plugins/markdown.js 가 번들에서 준다). -->
  <MdPreview
    :model-value="source || ''"
    :editor-id="previewId"
    :language="MD_LANGUAGE"
    no-mermaid
  />
</template>

<script setup>
import { useId } from 'vue'
import { MdPreview } from 'md-editor-v3'
import 'md-editor-v3/lib/preview.css'
import { MD_LANGUAGE } from '@/plugins/markdown'

defineProps({
  source: { type: String, default: '' }
})

// editorId 는 내부 이벤트 버스의 키이자 DOM id 다. 한 화면에 여러 개가 뜨는 곳이
// 있어(문제 설명·입력 설명·출력 설명·힌트) 기본값을 그대로 쓰면 서로 간섭한다.
const previewId = `md-view-${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`
</script>
