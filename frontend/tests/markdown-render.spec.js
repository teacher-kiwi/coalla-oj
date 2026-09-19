import { describe, it, expect } from 'vitest'
import { createApp, h, nextTick } from 'vue'
import { MdPreview } from 'md-editor-v3'
import { configureMarkdown, MD_LANGUAGE } from '@/plugins/markdown'

configureMarkdown()

function preview (source) {
  const el = document.createElement('div')
  document.body.appendChild(el)
  createApp(() => h(MdPreview, {
    modelValue: source,
    editorId: 'test-preview',
    language: MD_LANGUAGE,
    noMermaid: true,
    // 아이콘만 파일을 받아 쓴다. 테스트 DOM 은 스크립트를 실행하지 않으니 끄고,
    // 그 주소가 우리 서버인지는 markdown.spec.js 가 본다.
    noIconfont: true
  })).mount(el)
  return el
}

describe('저장된 마크다운 그리기', () => {
  it('수식과 코드를 번들에 든 라이브러리로 그린다', async () => {
    const el = preview('$x^2$\n\n```python\nprint(1)\n```')
    await nextTick()
    // katex·hljs 인스턴스를 못 받았으면 수식은 글자로, 코드는 색 없이 나온다
    expect(el.innerHTML).toContain('class="katex"')
    expect(el.innerHTML).toContain('hljs-')
  })

  it('화면을 그리면서 밖에서 무엇도 받아오지 않는다', async () => {
    preview('$x^2$\n\n```python\nprint(1)\n```')
    await nextTick()
    const external = Array.from(document.querySelectorAll('script[src], link[href]'))
      .map((node) => node.getAttribute('src') || node.getAttribute('href'))
      .filter((url) => /^https?:/.test(url))
    expect(external).toEqual([])
  })
})
