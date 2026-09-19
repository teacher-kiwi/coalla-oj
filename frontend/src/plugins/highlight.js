// 코드 하이라이트. 여기서 만든 hljs 인스턴스 하나를 마크다운 렌더(md-editor-v3)와
// 제출 코드 보기(v-highlight)가 함께 쓴다.
//
// md-editor-v3 는 인스턴스를 주지 않으면 unpkg 에서 highlight.min.js 와 테마
// css 를 받아온다(plugins/markdown.js 에서 이 인스턴스를 넘긴다). 학교 망에서
// 외부 CDN 이 막히거나 느리면 문제 설명의 코드가 색 없이 나오므로 번들에 담는다.
import hljs from 'highlight.js/lib/core'
import c from 'highlight.js/lib/languages/c'
import cpp from 'highlight.js/lib/languages/cpp'
import go from 'highlight.js/lib/languages/go'
import java from 'highlight.js/lib/languages/java'
import javascript from 'highlight.js/lib/languages/javascript'
import python from 'highlight.js/lib/languages/python'
import 'highlight.js/styles/atom-one-light.css'

// 채점하는 언어(backend/judge/languages.py)를 모두 등록한다.
// 등록하지 않은 언어는 hljs 가 추측(highlightAuto)으로 넘겨 엉뚱하게 칠한다.
hljs.registerLanguage('c', c)
hljs.registerLanguage('cpp', cpp)
hljs.registerLanguage('go', go)
hljs.registerLanguage('java', java)
hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('python', python)

// 채점기가 쓰는 언어 이름과 hljs 의 이름이 다르다. 그대로 넘기면 hljs 가
// "Could not find the language" 를 찍고 색을 입히지 않는다.
const HLJS_NAMES = {
  C: 'c',
  'C++': 'cpp',
  Java: 'java',
  Python3: 'python',
  Golang: 'go',
  JavaScript: 'javascript',
  // 블록으로 짠 코드는 파이썬으로 채점하고 파이썬으로 보여준다
  'Block Coding': 'python'
}

export function hljsLanguage (name) {
  return HLJS_NAMES[name] || ''
}

export { hljs }

function highlight (el, binding) {
  Array.from(el.querySelectorAll('code')).forEach((target) => {
    if (binding.value) {
      target.textContent = binding.value
    }
    hljs.highlightElement(target)
  })
}

export default {
  install (app) {
    app.directive('highlight', {
      mounted: highlight,
      updated: highlight
    })
  }
}
