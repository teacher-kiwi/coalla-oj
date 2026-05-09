<template>
  <div class="container">
    <div>
      <SideMenu />
    </div>
    <div id="header">
      <el-icon class="katex-icon" @click="katexVisible=true"><EditPen /></el-icon>
      <ScreenFull :width="14" :height="14" class="screen-full" />
      <el-dropdown @command="handleCommand">
        <span class="el-dropdown-link">
          {{ user.username }}
          <el-icon><ArrowDown /></el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="logout">Logout</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
    <div class="content-app">
      <router-view v-slot="{ Component }">
        <transition name="fadeInUp" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
      <div class="footer">
        Build Version: {{ version }}
      </div>
    </div>

    <el-dialog :title="t('m.Latex_Editor')" v-model="katexVisible">
      <KatexEditor />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ArrowDown, EditPen } from '@element-plus/icons-vue'
import SideMenu from '../components/SideMenu.vue'
import ScreenFull from '@admin/components/ScreenFull.vue'
import KatexEditor from '@admin/components/KatexEditor.vue'
import api from '../api'
import { useUserStore } from '@/store/user'

const { t } = useI18n()
const router = useRouter()
const userStore = useUserStore()

const version = import.meta.env.VITE_APP_VERSION || 'dev'
const katexVisible = ref(false)

const user = computed(() => userStore.user)

function handleCommand (command) {
  if (command === 'logout') {
    api.logout().then(() => {
      router.push({ name: 'login' })
    })
  }
}

onMounted(() => {
  api.getProfile().then(res => {
    if (!res.data.data) {
      router.push({ name: 'login' })
    } else {
      userStore.changeProfile(res.data.data)
    }
  })
})
</script>

<style lang="less">
  a {
    background-color: transparent;
  }

  a:active, a:hover {
    outline-width: 0
  }

  img {
    border-style: none
  }

  .container {
    overflow: auto;
    font-weight: 400;
    height: 100%;
    -webkit-font-smoothing: antialiased;
    background-color: #EDECEC;
    overflow-y: scroll;
    min-width: 1000px;
  }

  * {
    box-sizing: border-box;
  }

  .katex-icon {
    margin-right: 5px;
    cursor: pointer;
  }

  #header {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    padding-left: 210px;
    padding-right: 30px;
    height: 50px;
    background: #F9FAFC;
    .screen-full {
      margin-right: 8px;
    }
  }

  .content-app {
    padding-top: 20px;
    padding-right: 10px;
    padding-left: 210px;
  }

  .footer {
    margin: 15px;
    text-align: center;
    font-size: small;
  }

  @keyframes fadeInUp {
    from {
      opacity: 0;
      transform: translate(0, 30px);
    }

    to {
      opacity: 1;
      transform: none;
    }
  }

  .fadeInUp-enter-active {
    animation: fadeInUp .8s;
  }
</style>
