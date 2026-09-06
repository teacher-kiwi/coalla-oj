<template>
  <div>
    <NavBar />
    <div class="content-app">
      <router-view v-slot="{ Component }">
        <transition name="fadeInUp" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
      <div class="footer">
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
  .content-app {
    margin-top: 80px;
    padding: 0 2%;
  }

  .footer {
    margin-top: 20px;
    margin-bottom: 10px;
    text-align: center;
    font-size: small;
  }

  .fadeInUp-enter-active {
    animation: fadeInUp .8s;
  }
</style>
