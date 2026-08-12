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
      <el-sub-menu v-if="userStore.isTeacher" index="teacher">
        <template #title>
          <el-icon><School /></el-icon>
          수업
        </template>
        <el-menu-item index="/teacher/class">내 학급</el-menu-item>
        <el-menu-item index="/teacher/problem-set">문제집</el-menu-item>
        <el-menu-item index="/teacher/progress">학습 현황</el-menu-item>
      </el-sub-menu>
      <!-- 수업용 학생만 보인다. 개인 학생(구글 가입)은 배포받을 학급이 없다. -->
      <el-menu-item v-if="isStudent" index="/problem-set">
        <el-icon><Notebook /></el-icon>
        문제집
      </el-menu-item>
      <!-- OI 순위(/oi-rank)는 대회를 쓰기 시작하면 되살릴 수 있게 라우트만 남기고 메뉴에서 내렸다 -->
      <el-menu-item index="/acm-rank">
        <el-icon><Medal /></el-icon>
        순위
      </el-menu-item>
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
import { Notebook, School } from '@element-plus/icons-vue'
import { useUserStore } from '@/store/user'
import Login from '@oj/views/user/Login.vue'
const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const userStore = useUserStore()

onMounted(() => {
  userStore.getProfile()
})

const activeMenu = computed(() => {
  // 교사 메뉴는 하위 항목(/teacher/class, /teacher/problem-set)이 각각 활성화되어야 한다
  const [, first, second] = route.path.split('/')
  return first === 'teacher' ? `/teacher/${second || 'class'}` : '/' + first
})

// 학급 소속 여부는 프로필에 없지만, 수업용 학생은 교사가 만든 계정이라 created_by 가 있다
const isStudent = computed(() => !!userStore.user.created_by)

const modalVisible = computed({
  get: () => appStore.modalStatus.visible,
  set: (value) => appStore.changeModalStatus({ visible: value })
})

// 가입은 구글 로그인 안에서 처리하므로 모달은 로그인 하나뿐이다
const currentModal = computed(() => Login)

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
