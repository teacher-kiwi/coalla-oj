// 다른 사람이 입은 아이템(모습) 모음. 순위표·채점 현황처럼 여러 사람이 한꺼번에 나오는
// 화면에서 CharacterAvatar 가 아이디만으로 모습을 찾는다.
//
// 같은 순간에 그려지는 캐릭터의 아이디를 모아 요청 한 번(최대 100명씩)으로 묻는다.
// 한 번 받은 모습은 새로고침 전까지 다시 묻지 않는다. 내 모습은 샵에서 바꾸면 setLook 으로 바로 고친다.
import { reactive } from 'vue'
import axios from 'axios'
import { itemFromRecord } from './character'

const LIMIT = 100
const EMPTY = Object.freeze({})

// 아이디 → { 자리: 아이템 id }. 받아 온 뒤에만 들어간다.
const looks = reactive({})
// 이미 물은 아이디. 그리는 중(computed 안)에 반응형 값을 바꾸지 않으려고 따로 둔다.
const asked = new Set()
// 아이템 id → 그리기용 아이템
const items = new Map()
let waiting = new Set()
let timer = null

function keep (record) {
  const old = items.get(record.id)
  if (!old || old.v !== record.last_update_time) items.set(record.id, itemFromRecord(record))
}

function flush () {
  timer = null
  const names = [...waiting]
  waiting = new Set()
  for (let i = 0; i < names.length; i += LIMIT) {
    const chunk = names.slice(i, i + LIMIT)
    axios.get('avatar/looks', { params: { usernames: chunk.join(',') } }).then(res => {
      const data = (res.data && !res.data.error && res.data.data) || { looks: {}, items: {} }
      Object.values(data.items || {}).forEach(keep)
      chunk.forEach(u => { looks[u] = (data.looks || {})[u] || EMPTY })
    }, () => {
      // 실패하면 기본 모습으로 둔다(다시 묻지 않는다)
      chunk.forEach(u => { looks[u] = EMPTY })
    })
  }
}

/** 이 아이디가 입은 아이템 { 자리: 그리기용 아이템 }. 처음 물으면 빈 값을 주고, 받아 오면 다시 그려진다. */
export function lookOf (username) {
  if (!username) return EMPTY
  if (!asked.has(username)) {
    asked.add(username)
    waiting.add(username)
    if (!timer) timer = setTimeout(flush)
  }
  const ids = looks[username]
  if (!ids) return EMPTY
  const eq = {}
  for (const [slot, id] of Object.entries(ids)) if (items.has(id)) eq[slot] = items.get(id)
  return eq
}

/** 내 모습을 바꾼 뒤 부른다. equipped: { 자리: id }, records: 서버 아이템 목록(입은 것이 들어 있어야 함) */
export function setLook (username, equipped, records = []) {
  records.forEach(keep)
  asked.add(username)
  looks[username] = { ...equipped }
}
