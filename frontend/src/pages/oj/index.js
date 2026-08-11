import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import ko from 'element-plus/es/locale/lang/ko'
// 아이콘은 1000개 전부가 아니라 전역 해석이 필요한 것만 등록한다.
// (템플릿에서 태그로 쓰거나, IconBtn/InfoCard 에 문자열 이름으로 넘기는 것들)
import {
  ArrowDown, Grid, HomeFilled, InfoFilled, Medal, TrendCharts, Trophy,
  Key, Lock, Message, User
} from '@element-plus/icons-vue'
import VChart from 'vue-echarts'
import 'element-plus/dist/index.css'

// echarts 는 전체를 불러오지 않고 실제로 쓰는 것만 등록한다.
// (원형: 문제 통계 / 막대·꺾은선: 순위 · 대회 순위)
import { use } from 'echarts/core'
import { PieChart, BarChart, LineChart } from 'echarts/charts'
import {
  TooltipComponent, LegendComponent, GridComponent,
  ToolboxComponent, DataZoomComponent, MarkPointComponent
} from 'echarts/components'
import { LabelLayout } from 'echarts/features'
import { CanvasRenderer } from 'echarts/renderers'

use([
  PieChart, BarChart, LineChart,
  TooltipComponent, LegendComponent, GridComponent,
  ToolboxComponent, DataZoomComponent, MarkPointComponent,
  LabelLayout, CanvasRenderer
])

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

for (const [key, component] of Object.entries({
  ArrowDown, Grid, HomeFilled, InfoFilled, Medal, TrendCharts, Trophy,
  Key, Lock, Message, User
})) {
  app.component(key, component)
}

app.component('VChart', VChart)
app.component('Panel', Panel)
app.component('VerticalMenu', VerticalMenu)
app.component('VerticalMenuItem', VerticalMenuItem)

app.mount('#app')
