import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import ko from 'element-plus/es/locale/lang/ko'
// 아이콘은 1000개 전부가 아니라 전역 해석이 필요한 것만 등록한다.
// (템플릿에서 태그로 쓰거나, IconBtn/InfoCard 에 문자열 이름으로 넘기는 것들)
import {
  CaretTop, CopyDocument, Delete, Document, Download, Edit, InfoFilled,
  List, Menu, Odometer, Plus, Trophy, User
} from '@element-plus/icons-vue'
import 'element-plus/dist/index.css'

import App from './App.vue'
import router from './router'
import katex from '@/plugins/katex'

import Panel from './components/Panel.vue'
import IconBtn from './components/btn/IconBtn.vue'
import Save from './components/btn/Save.vue'
import Cancel from './components/btn/Cancel.vue'
import '@/styles/index.less'
import './style.less'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: ko })
app.use(katex)

for (const [key, component] of Object.entries({
  CaretTop, CopyDocument, Delete, Document, Download, Edit, InfoFilled,
  List, Menu, Odometer, Plus, Trophy, User
})) {
  app.component(key, component)
}

app.component('Panel', Panel)
app.component('IconBtn', IconBtn)
app.component('Save', Save)
app.component('Cancel', Cancel)

app.mount('#app')
