import js from '@eslint/js'
import vue from 'eslint-plugin-vue'
import globals from 'globals'

// 서식(따옴표·세미콜론·속성 줄바꿈)은 검사하지 않는다.
// vue 의 flat/recommended 를 켜면 서식 경고만 2천 건 넘게 나오는데, 이 코드베이스는
// 상위 프로젝트에서 온 파일과 직접 쓴 blockly 파일의 스타일이 원래 다르다.
// 여기서는 "버그가 되는 것"만 본다: 미사용 변수, 정의되지 않은 변수, v-for 의 key 누락 등.
export default [
  {
    ignores: ['dist/**', 'node_modules/**']
  },
  js.configs.recommended,
  ...vue.configs['flat/essential'],
  {
    // 브라우저에서 도는 코드
    files: ['src/**/*.{js,vue}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: globals.browser
    }
  },
  {
    // 빌드 설정과 점검 스크립트는 node 에서 돈다
    files: ['*.{js,mjs}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: globals.node
    }
  },
  {
    rules: {
      // Panel, Home, Login 처럼 한 단어 컴포넌트 이름을 쓰고 있다. 지금 와서 바꿀 이유가 없다.
      'vue/multi-word-component-names': 'off',
      // catch (e) 에서 e 를 안 쓰는 것은 흔한 형태라 넘어간다.
      // 의도적으로 안 쓰는 것은 _ 로 시작하게 한다. 특정 키만 빼고 나머지를 넘길 때
      // 쓰는 `const { a: _ignored, ...rest } = obj` 형태가 여기 해당한다.
      'no-unused-vars': ['error', {
        caughtErrors: 'none',
        argsIgnorePattern: '^_',
        varsIgnorePattern: '^_'
      }]
    }
  }
]
