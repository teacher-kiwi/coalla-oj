// 템플릿이 참조하지만 <script setup> 에 정의되지 않은 식별자를 찾는다.
// Vue 컴파일러는 이런 것을 _ctx.X 로 컴파일할 뿐 빌드를 실패시키지 않으므로,
// 런타임에서야 "_ctx.t is not a function" 같은 오류로 드러난다.
import * as compiler from 'vue/compiler-sfc'
import fs from 'fs'
import path from 'path'

const SRC = process.argv[2] || 'src'
// 템플릿에서 정상적으로 쓰이는 런타임 전역
const ALLOWED = new Set([
  '$slots', '$attrs', '$props', '$emit', '$refs', '$el', '$options', '$parent',
  '$root', '$data', '$forceUpdate', '$nextTick', '$watch', '$style'
])

function walk (dir, out = []) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name)
    if (e.isDirectory()) walk(p, out)
    else if (e.name.endsWith('.vue')) out.push(p)
  }
  return out
}

let problems = 0
let checked = 0

for (const file of walk(SRC)) {
  const source = fs.readFileSync(file, 'utf8')
  const { descriptor, errors } = compiler.parse(source, { filename: file })
  if (errors.length) {
    console.log(`✗ ${file}\n    SFC 파싱 오류: ${errors[0].message}`)
    problems++
    continue
  }
  if (!descriptor.template) continue

  let bindings
  try {
    if (descriptor.script || descriptor.scriptSetup) {
      bindings = compiler.compileScript(descriptor, { id: file }).bindings
    }
  } catch (e) {
    console.log(`✗ ${file}\n    script 컴파일 오류: ${e.message}`)
    problems++
    continue
  }

  let code
  try {
    code = compiler.compileTemplate({
      source: descriptor.template.content,
      filename: file,
      id: file,
      compilerOptions: { bindingMetadata: bindings }
    }).code
  } catch (e) {
    console.log(`✗ ${file}\n    template 컴파일 오류: ${e.message}`)
    problems++
    continue
  }

  checked++
  const undefined_ = [...new Set([...code.matchAll(/_ctx\.([A-Za-z_$][\w$]*)/g)].map(m => m[1]))]
    .filter(n => !ALLOWED.has(n))
  if (undefined_.length) {
    console.log(`✗ ${file}\n    템플릿이 쓰지만 정의되지 않음: ${undefined_.join(', ')}`)
    problems++
  }
}

console.log(`\n검사한 컴포넌트 ${checked}개, 문제 ${problems}건`)
process.exit(problems ? 1 : 0)
