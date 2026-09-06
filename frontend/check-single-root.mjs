// 라우트 화면의 템플릿이 요소 하나를 루트로 갖는지 검사한다.
//
// App.vue 가 router-view 를 <transition mode="out-in"> 으로 감싸고 있다. 이 모드는
// 떠나는 화면의 전환이 끝나야 다음 화면을 mount 하는데, 루트가 요소 하나가 아니면
// (주석이 루트 앞에 있거나 최상위 요소가 둘 이상이면) 전환 클래스를 붙일 대상이 없어
// "다 떠났다" 는 신호가 오지 않는다. 그러면 다음 화면이 영영 mount 되지 않아
// 빈 화면이 된다. Vue 는 경고도 내지 않고 빌드도 통과한다.
//
// 최상위 주석은 특히 눈에 띄지 않는다 - 개발 빌드에서는 주석도 노드로 남기 때문이다.
import * as compiler from 'vue/compiler-sfc'
import fs from 'fs'
import path from 'path'

const ROUTES = process.argv[2] || 'src/pages/oj/router/routes.js'
const SRC = process.argv[3] || 'src'

// routes.js 의 지연 import 에서 화면 파일 경로를 뽑는다
const routesSource = fs.readFileSync(ROUTES, 'utf8')
const files = new Set()
for (const [, spec] of routesSource.matchAll(/import\(\s*['"]([^'"]+)['"]\s*\)/g)) {
  const rel = spec.replace(/^@oj\//, 'pages/oj/').replace(/^@admin\//, 'pages/admin/')
                  .replace(/^@\//, '')
  const file = path.join(SRC, rel)
  if (fs.existsSync(file)) files.add(file)
}

let problems = 0
for (const file of [...files].sort()) {
  const { descriptor, errors } = compiler.parse(fs.readFileSync(file, 'utf8'), { filename: file })
  if (errors.length || !descriptor.template) continue

  // 공백 노드(type 2 이면서 비어 있음)는 컴파일러가 지운다. 남는 것만 센다.
  const roots = descriptor.template.ast.children.filter(
    node => !(node.type === 2 && !node.content.trim()))
  const elements = roots.filter(node => node.type === 1)

  if (roots.length !== 1 || elements.length !== 1) {
    const kinds = roots.map(n => (n.type === 3 ? '주석' : n.type === 1 ? `<${n.tag}>` : '글자'))
    console.log(`✗ ${file}\n    루트가 요소 하나가 아니다: ${kinds.join(', ')}` +
                '\n    (주석은 루트 요소 안으로 옮기세요)')
    problems++
  }
}

console.log(`\n라우트 화면 ${files.size}개, 문제 ${problems}건`)
process.exit(problems ? 1 : 0)
