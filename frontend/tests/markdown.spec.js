import { describe, it, expect } from 'vitest'
import MarkdownIt from 'markdown-it'
import { markdownItConfig, MD_LANGUAGE, KO_LANGUAGE } from '@/plugins/markdown'

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
