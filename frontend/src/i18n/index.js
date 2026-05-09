import { createI18n } from 'vue-i18n'

import { m as ojEnUS } from './oj/en-US'
import { m as ojZhCN } from './oj/zh-CN'
import { m as ojZhTW } from './oj/zh-TW'
import { m as ojKoKR } from './oj/ko-KR'

import { m as adminEnUS } from './admin/en-US'
import { m as adminZhCN } from './admin/zh-CN'
import { m as adminZhTW } from './admin/zh-TW'
import { m as adminKoKR } from './admin/ko-KR'

const languages = [
  { value: 'en-US', label: 'English' },
  { value: 'zh-CN', label: '简体中文' },
  { value: 'zh-TW', label: '繁體中文' },
  { value: 'ko-KR', label: '한국어' }
]

const messages = {
  'en-US': { m: { ...ojEnUS, ...adminEnUS } },
  'zh-CN': { m: { ...ojZhCN, ...adminZhCN } },
  'zh-TW': { m: { ...ojZhTW, ...adminZhTW } },
  'ko-KR': { m: { ...ojKoKR, ...adminKoKR } }
}

const i18n = createI18n({
  legacy: false,
  locale: 'ko-KR',
  fallbackLocale: 'en-US',
  messages
})

export default i18n
export { languages }
