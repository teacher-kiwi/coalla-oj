// 마크다운 렌더 설정. 편집기(MdEditor)와 표시 화면(MdPreview)이 같은 설정을 쓴다.
//
// 문제 설명·공지·대회 안내는 마크다운으로 저장하고 화면에서 렌더한다.
// md-editor-v3 는 내부에서 markdown-it 을 `html: true` 로 만든다. 그대로 두면
// 본문에 적은 <img src=x onerror=...> 가 실행되므로 여기서 끈다. 끄면 원시
// HTML 이 글자로 이스케이프되어, 저장된 글이 스크립트를 실행할 수 없다.
//
// 이 설정이 사라지면 XSS 가 다시 열린다. tests/markdown.spec.js 가 지킨다.
// config 만 쓰는데 'md-editor-v3' 에서 가져오면 편집기(MdEditor)까지 딸려와, 그것을
// 쓰지 않는 학생 화면 번들에도 CodeMirror 가 들어간다. 전용 진입점을 쓴다.
import { config } from 'md-editor-v3/lib/es/config.mjs'
import { hljs } from './highlight'

// 편집기와 미리보기가 함께 쓰는 언어 코드
export const MD_LANGUAGE = 'ko'

// md-editor-v3 는 zh-CN 과 en-US 만 내장하고 기본값이 zh-CN 이다. 그대로 두면
// 코드 블록의 복사 버튼이 "复制代码" 로 나온다(학생 화면에도 그대로 보인다).
//
// 정의하지 않은 항목은 라이브러리가 en-US 로 채우므로(deepMerge), 화면에
// 글자로 드러나는 것만 옮긴다. 도구모음 툴팁은 영어로 두어도 무방하다.
export const KO_LANGUAGE = {
  copyCode: {
    text: '복사',
    successTips: '복사했습니다',
    failTips: '복사하지 못했습니다'
  },
  linkModalTips: {
    linkTitle: '링크 넣기',
    imageTitle: '이미지 넣기',
    descLabel: '설명:',
    descLabelPlaceHolder: '설명을 입력하세요...',
    urlLabel: '주소:',
    urlLabelPlaceHolder: '주소를 입력하세요...',
    buttonOK: '확인'
  },
  clipModalTips: {
    title: '이미지 잘라서 올리기',
    buttonUpload: '올리기'
  },
  footer: {
    markdownTotal: '글자 수',
    scrollAuto: '스크롤 동기화'
  }
}

// md-editor-v3 가 만든 markdown-it 인스턴스를 넘겨받아 손보는 훅.
// 테스트가 직접 부를 수 있도록 따로 내보낸다.
export function markdownItConfig (md) {
  md.set({ html: false })
}

// 편집기와 미리보기가 쓰는 곁가지 라이브러리. 넘기지 않으면 화면이 뜰 때마다
// 밖에서 받아온다 - 아이콘은 at.alicdn.com, 나머지는 unpkg.com 이다.
// 학교 망에서 막히면 학생 화면의 코드 색과 수식, 도구모음 아이콘이 통째로 빠진다.
//
// 코드 색(hljs)은 번들에 든 인스턴스를 넘긴다. 코드 블록은 거의 모든 문제에 있다.
//
// 수식(katex)은 파일 주소로 넘긴다. 번들에 넣으면 JS 와 폰트 수십 개를 모든
// 방문자가 첫 화면에서 받는데, 지금 저장된 글에는 수식이 한 건도 없다.
// 주소로 두면 라이브러리가 필요할 때 받아가고, 받아오는 곳은 unpkg 가 아니라
// 우리 서버다(vite.config.js 가 dist/katex 로 복사한다).
// 테스트가 "수식은 우리 서버에서 받아온다" 를 지킬 수 있도록 내보낸다.
export const EDITOR_EXTENSIONS = {
  highlight: { instance: hljs },
  katex: { js: '/katex/katex.min.js', css: '/katex/katex.min.css' },
  iconfont: '/md-editor-icons.js'
}

export function configureMarkdown () {
  config({
    markdownItConfig,
    editorExtensions: EDITOR_EXTENSIONS,
    editorConfig: { languageUserDefined: { [MD_LANGUAGE]: KO_LANGUAGE } }
  })
}
