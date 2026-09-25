import { describe, it, expect } from 'vitest'
import { createApp, h, nextTick } from 'vue'
// 화면이 쓰는 것과 같은 진입점이라야 설정이 걸린 상태를 본다.
// 묶음 진입점('md-editor-v3')은 config 가 다른 인스턴스라 설정이 적용되지 않는다.
import MdPreview from 'md-editor-v3/lib/es/MdPreview.mjs'
import { configureMarkdown, MD_LANGUAGE, EDITOR_EXTENSIONS } from '@/plugins/markdown'

configureMarkdown()

function preview (source) {
  const el = document.createElement('div')
  document.body.appendChild(el)
  createApp(() => h(MdPreview, {
    modelValue: source,
    editorId: 'test-preview',
    language: MD_LANGUAGE,
    noMermaid: true,
    // 화면(Markdown.vue)과 같은 조건으로 그린다. 여기서 빠뜨리면 아래의
    // "무엇도 받아오지 않는다" 가 실제 화면을 지키지 못한다.
    noKatex: true,
    // 아이콘만 파일을 받아 쓴다. 테스트 DOM 은 스크립트를 실행하지 않으니 끄고,
    // 그 주소가 우리 서버인지는 markdown.spec.js 가 본다.
    noIconfont: true
  })).mount(el)
  return el
}

describe('저장된 마크다운 그리기', () => {
  it('코드를 번들에 든 라이브러리로 그린다', async () => {
    const el = preview('```python\nprint(1)\n```')
    await nextTick()
    // hljs 인스턴스를 못 받았으면 코드가 색 없이 나온다
    expect(el.innerHTML).toContain('hljs-')
  })

  it('수식 파일은 아예 받아오지 않는다', async () => {
    // 라이브러리는 내용에 수식이 있는지 보지 않고 화면마다 katex(74KB)를
    // 받아간다. 지금 저장된 글에 수식은 0건이라 no-katex 로 끈다.
    // 쓰게 되면 그 속성만 지우면 되고, 주소가 우리 서버를 가리키는지는 아래에서 본다.
    preview('$x^2$')
    await nextTick()
    const urls = Array.from(document.querySelectorAll('script[src], link[href]'))
      .map((node) => node.getAttribute('src') || node.getAttribute('href'))
    expect(urls.filter((url) => url.includes('katex'))).toEqual([])
  })

  it('수식을 다시 켜더라도 받아올 곳은 우리 서버다', () => {
    // 번들에 넣지 않고 주소로 넘긴다(plugins/markdown.js).
    // 기본값으로 두면 unpkg.com 을 부르는데 학교 망에서 막힌다.
    const { katex } = EDITOR_EXTENSIONS
    expect(katex.instance).toBeUndefined()
    expect(katex.js).toMatch(/^\//)
    expect(katex.css).toMatch(/^\//)
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
