// 템플릿이 전역 등록에 기대는 컴포넌트가 실제로 등록되어 있는지 확인한다.
// 전역 컴포넌트 해석은 런타임에 일어나므로 빌드가 잡아주지 않는다.
import * as compiler from 'vue/compiler-sfc'
import fs from 'fs'
import path from 'path'

const ENTRIES = {
  'src/pages/oj': 'src/pages/oj/index.js',
  'src/pages/admin': 'src/pages/admin/index.js'
}
// 프레임워크가 자체 등록하는 것들
const BUILTIN = /^(el-|router-|transition|component|keep-alive|teleport|suspense)/

function walk (d, o = []) {
  for (const e of fs.readdirSync(d, { withFileTypes: true })) {
    const p = path.join(d, e.name)
    if (e.isDirectory()) walk(p, o); else if (e.name.endsWith('.vue')) o.push(p)
  }
  return o
}

let bad = 0
for (const [dir, entry] of Object.entries(ENTRIES)) {
  const entrySrc = fs.readFileSync(entry, 'utf8')
  // app.component('X', ...) 와 Object.entries({ A, B }) 등록분을 모은다
  const registered = new Set()
  for (const m of entrySrc.matchAll(/app\.component\(\s*'([^']+)'/g)) registered.add(m[1])
  for (const m of entrySrc.matchAll(/Object\.entries\(\{([\s\S]*?)\}\)/g)) {
    for (const name of m[1].split(/[,\s]+/).filter(Boolean)) registered.add(name)
  }

  // 공용 디렉터리(components/store 등)도 각 엔트리에서 쓰이므로 함께 훑는다
  const files = [...walk(dir), ...walk('src/store').filter(() => false)]
  const required = new Map()
  for (const f of files) {
    const { descriptor } = compiler.parse(fs.readFileSync(f, 'utf8'), { filename: f })
    if (!descriptor.template) continue
    let bindings
    try {
      if (descriptor.script || descriptor.scriptSetup) bindings = compiler.compileScript(descriptor, { id: f }).bindings
    } catch { /* 무시 */ }
    const { code } = compiler.compileTemplate({
      source: descriptor.template.content, filename: f, id: f, compilerOptions: { bindingMetadata: bindings }
    })
    for (const m of code.matchAll(/_resolveComponent\("([^"]+)"/g)) {
      if (!BUILTIN.test(m[1])) required.set(m[1], f)
    }
    // IconBtn / InfoCard 에 문자열로 넘기는 아이콘 이름
    for (const m of descriptor.template.content.matchAll(/\sicon="([A-Z][A-Za-z]*)"/g)) {
      required.set(m[1], f)
    }
  }

  // <icon-btn> ↔ IconBtn 처럼 케밥/파스칼 표기를 같은 것으로 본다
  const pascal = (n) => n.replace(/(^|-)(\w)/g, (_, __, c) => c.toUpperCase())
  const registeredPascal = new Set([...registered].map(pascal))
  const missing = [...required].filter(([name]) => !registered.has(name) && !registeredPascal.has(pascal(name)))
  console.log(`${entry}: 필요 ${required.size}개 / 등록 ${registered.size}개`)
  for (const [name, f] of missing) { console.log(`  ✗ ${name} 등록 안 됨 (${f})`); bad++ }
}
console.log(bad ? `\n문제 ${bad}건` : '\n문제 없음')
process.exit(bad ? 1 : 0)
