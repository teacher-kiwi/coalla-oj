import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import ko from 'element-plus/es/locale/lang/ko'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import VChart from 'vue-echarts'
import 'echarts'
import 'element-plus/dist/index.css'

import App from './App.vue'
import router from './router'
import highlight from '@/plugins/highlight'
import katex from '@/plugins/katex'

import Panel from '@oj/components/Panel.vue'
import VerticalMenu from '@oj/components/verticalMenu/verticalMenu.vue'
import VerticalMenuItem from '@oj/components/verticalMenu/verticalMenu-item.vue'
import '@/styles/index.less'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: ko })
app.use(highlight)
app.use(katex)

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.component('VChart', VChart)
app.component('Panel', Panel)
app.component('VerticalMenu', VerticalMenu)
app.component('VerticalMenuItem', VerticalMenuItem)

app.mount('#app')
