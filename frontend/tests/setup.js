// Node 22 는 실험적인 전역 localStorage 를 노출한다. 실행 시 `--localstorage-file`
// 경로가 제대로 주어지지 않으면 getItem/setItem 만 있고 clear() 같은 메서드가 없는
// 반쪽짜리 객체가 되는데, 이것이 happy-dom 이 만든 구현을 가려버린다.
// 그러면 src/utils/storage.js 가 모듈을 읽는 시점에 그 반쪽짜리를 붙잡아
// "localStorage.clear is not a function" 으로 죽는다.
//
// 노드 버전에 따라 테스트 결과가 달라지지 않도록, 테스트에서는 항상 이 구현을 쓴다.
// (storage.js 가 import 시점에 window.localStorage 를 캡처하므로 테스트 파일보다
//  먼저 실행되는 setupFiles 에서 덮어써야 한다)
function createMemoryStorage () {
  const data = new Map()
  return {
    getItem (key) {
      return data.has(String(key)) ? data.get(String(key)) : null
    },
    setItem (key, value) {
      data.set(String(key), String(value))
    },
    removeItem (key) {
      data.delete(String(key))
    },
    clear () {
      data.clear()
    },
    key (index) {
      return [...data.keys()][index] ?? null
    },
    get length () {
      return data.size
    }
  }
}

const storage = createMemoryStorage()
const targets = new Set([globalThis, globalThis.window].filter(Boolean))
for (const target of targets) {
  Object.defineProperty(target, 'localStorage', {
    value: storage,
    configurable: true,
    writable: true
  })
}
