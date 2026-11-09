<template>
  <div>
    <NavBar v-if="!route.meta.homework" />
    <div :class="['content-app', { 'content-hw': route.meta.homework }]">
      <router-view v-slot="{ Component }">
        <transition name="fadeInUp" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
      <!-- 바로 과제 화면은 학생이 과제만 보도록 사이트 바닥글도 감춘다 -->
      <div v-if="!route.meta.homework" class="footer">
        <Markdown :source="appStore.website.website_footer" />
        <p>Powered by <a href="https://github.com/QingdaoU/OnlineJudge">OnlineJudge</a>
          <span v-if="version">&nbsp; Version: {{ version }}</span>
        </p>
      </div>
    </div>
    <el-backtop :right="40" :bottom="40" />
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import Markdown from '@oj/components/Markdown.vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAppStore } from '@/store/app'
import NavBar from '@oj/components/NavBar.vue'

const appStore = useAppStore()
const route = useRoute()
const version = ref(import.meta.env.VITE_VERSION || '')
const { website } = storeToRefs(appStore)

try {
  const loader = document.getElementById('app-loader')
  if (loader) loader.remove()
} catch (e) {
  // 무시한다
}

function updateTitle () {
  const title = route.meta?.title
  if (title) appStore.changeDomTitle(title)
}

onMounted(() => {
  appStore.getWebsiteConfig()
})

watch(website, updateTitle)
watch(() => route.fullPath, updateTitle)
</script>

<style lang="less">
  * {
    -webkit-box-sizing: border-box;
    -moz-box-sizing: border-box;
    box-sizing: border-box;
  }

  a {
    text-decoration: none;
    background-color: transparent;
    &:active, &:hover {
      outline-width: 0;
    }
  }

  // 내비게이션은 화면에 고정되어 있고 높이가 60px 로 일정하다
  // (el-menu 의 가로 모드는 줄바꿈하지 않는다). 그만큼 본문을 내린다.
  // 예전에는 좁은 화면에서 내비가 두 줄이 된다고 보고 160px 를 줬는데,
  // 두 줄이 되지 않아 1200px 아래에서 100px 가 그냥 비어 있었다.
  // 본문 폭은 모든 화면이 같다. 넓은 모니터에서 표가 끝없이 벌어지지 않게 1440px 에서 멈춘다.
  // (예전에는 홈·순위만 따로 91% 로 좁혀서, 메뉴를 옮길 때마다 카드 왼쪽 끝이 움직였다)
  .content-app {
    max-width: 1440px;
    margin: 80px auto 0;
    padding: 0 24px;
  }
  @media (max-width: 1000px) {
    .content-app {
      padding: 0 16px;
    }
  }

  // 바로 과제 화면은 상단 메뉴가 없다. 메뉴 자리만큼 내리지 않는다.
  .content-hw {
    margin-top: 0;
    padding-top: 24px;
    padding-bottom: 40px;
  }

  // 바닥글은 카드처럼 보이지 않게 바탕 위에 옅게 둔다
  .footer {
    margin: 32px 0 16px;
    text-align: center;
    font-size: 13px;
    color: #909399;
    line-height: 1.6;
    p {
      margin: 0;
    }
    // 사이트 설정의 바닥글 글은 마크다운 미리보기로 그린다. 그 흰 바탕·여백을 걷어낸다.
    .md-editor {
      background: transparent;
    }
    .md-editor-preview-wrapper, .md-editor-preview {
      padding: 0;
      font-size: 13px;
      color: inherit;
    }
    a {
      color: inherit;
      text-decoration: underline;
      &:hover {
        color: var(--el-color-primary);
      }
    }
  }

  .fadeInUp-enter-active {
    animation: fadeInUp .8s;
  }
</style>
