<template>
  <div id="header">
    <el-menu
      :default-active="activeMenu"
      mode="horizontal"
      class="oj-menu"
      :ellipsis="false"
      @select="handleRoute"
    >
      <div class="logo"><span>{{ appStore.website.website_name }}</span></div>
      <el-menu-item index="/">
        <el-icon><HomeFilled /></el-icon>
        홈
      </el-menu-item>
      <el-menu-item index="/problem">
        <el-icon><Grid /></el-icon>
        문제
      </el-menu-item>
      <el-menu-item index="/contest">
        <el-icon><Trophy /></el-icon>
        대회
      </el-menu-item>
      <el-menu-item index="/status">
        <el-icon><TrendCharts /></el-icon>
        채점
      </el-menu-item>
      <el-sub-menu index="rank">
        <template #title>
          <el-icon><Medal /></el-icon>
          순위
        </template>
        <el-menu-item index="/acm-rank">ACM 순위</el-menu-item>
        <el-menu-item index="/oi-rank">OI 순위</el-menu-item>
      </el-sub-menu>
      <el-sub-menu index="about">
        <template #title>
          <el-icon><InfoFilled /></el-icon>
          정보
        </template>
        <el-menu-item index="/about">채점기</el-menu-item>
        <el-menu-item index="/faq">자주 묻는 질문</el-menu-item>
      </el-sub-menu>

      <div class="flex-spacer" />

      <div v-if="!userStore.isAuthenticated" class="btn-menu">
        <el-button round @click="handleBtnClick('login')">로그인</el-button>
        <el-button
          v-if="appStore.website.allow_register"
          round
          @click="handleBtnClick('register')"
          class="btn-register"
        >
          회원가입
        </el-button>
      </div>
      <el-dropdown v-else class="drop-menu" trigger="click" @command="handleRoute">
        <el-button text class="drop-menu-title">
          {{ userStore.user.username }}
          <el-icon><ArrowDown /></el-icon>
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="/user-home">프로필</el-dropdown-item>
            <el-dropdown-item command="/status?myself=1">내 채점</el-dropdown-item>
            <el-dropdown-item command="/setting/profile">설정</el-dropdown-item>
            <el-dropdown-item v-if="userStore.isAdminRole" command="/admin">관리자 페이지</el-dropdown-item>
            <el-dropdown-item divided command="/logout">로그아웃</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </el-menu>

    <el-dialog v-model="modalVisible" :width="400" :show-close="true">
      <template #header>
        <div class="modal-title">환영합니다 {{ appStore.website.website_name_shortcut }}</div>
      </template>
      <component :is="currentModal" v-if="modalVisible" />
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/store/app'
import { useUserStore } from '@/store/user'
import Login from '@oj/views/user/Login.vue'
import Register from '@oj/views/user/Register.vue'
const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const userStore = useUserStore()

onMounted(() => {
  userStore.getProfile()
})

const activeMenu = computed(() => '/' + route.path.split('/')[1])

const modalVisible = computed({
  get: () => appStore.modalStatus.visible,
  set: (value) => appStore.changeModalStatus({ visible: value })
})

const currentModal = computed(() => {
  return appStore.modalStatus.mode === 'register' ? Register : Login
})

function handleRoute (target) {
  if (!target) return
  if (target.indexOf('admin') < 0) {
    router.push(target)
  } else {
    window.open('/admin/')
  }
}

function handleBtnClick (mode) {
  appStore.changeModalStatus({ visible: true, mode })
}
</script>

<style lang="less" scoped>
  #header {
    min-width: 300px;
    position: fixed;
    top: 0;
    left: 0;
    height: auto;
    width: 100%;
    z-index: 1000;
    background-color: #fff;
    box-shadow: 0 1px 5px 0 rgba(0, 0, 0, 0.1);

    .oj-menu {
      background: #fdfdfd;
      display: flex;
      align-items: center;
    }

    .logo {
      margin-left: 2%;
      margin-right: 2%;
      font-size: 20px;
      line-height: 60px;
    }

    .flex-spacer {
      flex: 1;
    }

    .drop-menu {
      margin-right: 30px;
      &-title {
        font-size: 18px;
      }
    }

    .btn-menu {
      font-size: 16px;
      margin-right: 10px;
      .btn-register {
        margin-left: 5px;
      }
    }
  }

  .modal-title {
    font-size: 18px;
    font-weight: 600;
  }
</style>
