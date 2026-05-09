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
        <p v-html="appStore.website.website_footer"></p>
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
  // noop
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

  @media screen and (max-width: 1200px) {
    .content-app {
      margin-top: 160px;
      padding: 0 2%;
    }
  }

  @media screen and (min-width: 1200px) {
    .content-app {
      margin-top: 80px;
      padding: 0 2%;
    }
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
