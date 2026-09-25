import { existsSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, it, expect, vi } from 'vitest'
import MarkdownIt from 'markdown-it'
import { hljs } from '@/plugins/highlight'

// 설정으로 무엇을 넘기는지 보려고 라이브러리의 config 만 가로챈다.
// 편집기까지 딸려오지 않도록 전용 진입점에서 가져오므로 그 경로를 가로챈다.
vi.mock('md-editor-v3/lib/es/config.mjs', () => ({ config: vi.fn() }))
const { config } = await import('md-editor-v3/lib/es/config.mjs')
const { markdownItConfig, MD_LANGUAGE, KO_LANGUAGE, configureMarkdown } =
  await import('@/plugins/markdown')

// md-editor-v3 는 html 을 켠 채로 markdown-it 을 만들고, 그 인스턴스를
// markdownItConfig 훅에 넘겨준다(lib/es/chunks/index.mjs). 같은 순서를 재현한다.
function buildRenderer () {
  const md = new MarkdownIt({ html: true, breaks: true, linkify: true })
  markdownItConfig(md)
  return md
}

describe('마크다운 렌더 설정', () => {
  const md = buildRenderer()

  it('본문에 적은 원시 HTML 은 실행되지 않고 글자로 남는다', () => {
    // 이 테스트가 깨지면 html 옵션이 다시 켜진 것이다. XSS 가 함께 열린다.
    // 글자로 남는 것은 무해하므로, 태그가 살아 있는지(꺾쇠가 안 열렸는지)를 본다.
    expect(md.render('<img src=x onerror=alert(1)>')).not.toContain('<img')
    expect(md.render('<script>alert(1)</script>')).not.toContain('<script')

    const overlay = md.render('<p style="position:fixed;width:100vw">덮기</p>')
    expect(overlay).not.toContain('<p style=')
    expect(overlay).toContain('&lt;p style=')
  })

  it('마크다운 문법은 그대로 동작한다', () => {
    expect(md.render('**굵게**')).toContain('<strong>굵게</strong>')
    expect(md.render('`코드`')).toContain('<code>코드</code>')
    expect(md.render('- 하나\n- 둘')).toContain('<li>')
  })

  it('javascript: 링크는 링크로 만들지 않는다', () => {
    expect(md.render('[클릭](javascript:alert(1))')).not.toContain('href="javascript:')
  })
})

describe('편집기 언어', () => {
  it('한국어 언어팩을 쓴다', () => {
    // md-editor-v3 의 기본 언어는 zh-CN 이다. 언어를 넘기지 않으면 코드 블록에
    // "复制代码" 가 붙어 학생 화면에 그대로 보인다.
    expect(MD_LANGUAGE).toBe('ko')
  })

  it('학생 화면에 글자로 드러나는 항목이 한국어다', () => {
    expect(KO_LANGUAGE.copyCode.text).toBe('복사')
    for (const value of Object.values(KO_LANGUAGE.copyCode)) {
      expect(value).not.toMatch(/[\u4e00-\u9fff]/)
    }
  })
})

describe('편집기가 쓰는 곁가지 라이브러리', () => {
  it('코드 색은 번들에 든 것을 넘겨 화면마다 CDN 을 부르지 않는다', () => {
    // 넘기지 않으면 라이브러리가 unpkg.com 에서 받아온다. 학교 망에서 막히면
    // 학생 화면의 코드 색이 통째로 빠진다. 코드 블록은 거의 모든 문제에 있다.
    configureMarkdown()
    const { editorExtensions } = config.mock.calls[0][0]
    expect(editorExtensions.highlight.instance).toBe(hljs)
  })

  it('수식은 번들에 넣지 않고 우리 서버 주소로 넘긴다', () => {
    // 번들에 넣으면 JS 와 폰트 수십 개를 모든 방문자가 첫 화면에서 받는다.
    // 주소로 두면 수식이 있는 글에서만 받아가고, 그 곳이 unpkg 가 아니라
    // 우리 서버여야 학교 망에서도 뜬다(vite.config.js 가 dist/katex 로 복사한다).
    configureMarkdown()
    const { katex } = config.mock.calls[0][0].editorExtensions
    expect(katex.instance).toBeUndefined()
    expect(katex.js.startsWith('/')).toBe(true)
    expect(katex.css.startsWith('/')).toBe(true)
  })

  it('아이콘은 받아 둔 파일을 같은 서버에서 준다', () => {
    // 기본값은 at.alicdn.com 이다. 주소가 우리 서버를 가리키는데 파일이 없으면
    // 도구모음 아이콘이 전부 빈칸이 되므로 파일이 있는지도 함께 본다.
    configureMarkdown()
    const { iconfont } = config.mock.calls[0][0].editorExtensions
    expect(iconfont.startsWith('/')).toBe(true)
    const here = dirname(fileURLToPath(import.meta.url))
    expect(existsSync(resolve(here, '..', `public${iconfont}`))).toBe(true)
  })
})
