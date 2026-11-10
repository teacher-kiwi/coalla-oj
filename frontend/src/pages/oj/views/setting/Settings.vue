<template>
  <div class="container">
    <el-card :body-style="{ padding: 0 }">
      <div class="flex-container">
        <div class="menu">
          <el-menu :default-active="activeName" @select="goRoute" class="setting-menu">
            <div class="me">
              <CharacterAvatar v-if="userStore.user.username" :username="userStore.user.username"
                               mode="full" :size="128" />
            </div>

            <el-menu-item v-if="isStudent" index="/setting/password">비밀번호 변경</el-menu-item>
            <template v-else>
              <el-menu-item index="/setting/account">계정</el-menu-item>
              <el-menu-item index="/setting/security">보안</el-menu-item>
            </template>
            <el-menu-item v-if="showTeacherMenu" index="/setting/teacher">교사 인증</el-menu-item>
          </el-menu>
        </div>
        <div class="panel">
          <router-view v-slot="{ Component }">
            <transition name="fadeInUp">
              <component :is="Component" />
            </transition>
          </router-view>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, watchEffect } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import CharacterAvatar from '@oj/components/CharacterAvatar.vue'
import { useUserStore } from '@/store/user'
const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const activeName = computed(() => route.path)
// 학교에서 발급받은 학생 계정에는 교사 신청을 노출하지 않는다
// 학교에서 발급받은 계정(학생)은 이메일·구글 연동이 없어 다른 설정이 의미 없다
const isStudent = computed(() => !!userStore.user.created_by)
const showTeacherMenu = computed(() => !isStudent.value)

// 학생 메뉴에는 비밀번호 변경만 있다. 메뉴에서 감추는 것만으로는 주소창으로
// 직접 들어오는 것을 막지 못하므로 되돌린다.
// (프로필이 도착하기 전에는 학생인지 알 수 없어 기다린다)
watchEffect(() => {
  if (!userStore.profileReady) return
  if (isStudent.value && route.path !== '/setting/password') {
    router.replace('/setting/password')
  }
})

function goRoute (path) {
  router.push(path)
}
</script>

<style lang="less" scoped>
  // 다른 화면과 같은 본문 폭을 쓰되 너무 벌어지지 않게 1100px 에서 멈춘다.
  // (예전 min-width: 800px 은 태블릿 세로 폭에서 화면을 넘겼다)
  .container {
    max-width: 1100px;
    margin: auto;
  }

  .setting-menu {
    text-align: center;
  }

  .flex-container {
    display: flex;
    .menu {
      flex: 1 0 150px;
      max-width: 250px;
      // 프로필 사진 대신 캐릭터. 사진 올리기는 캐릭터로 바꾸면서 없앴다.
      .me {
        display: flex;
        justify-content: center;
        padding: 20px 0 12px;
      }
    }
    .panel {
      flex: auto;
    }
  }
</style>

<style lang="less">
  .setting-main {
    position: relative;
    margin: 10px 40px;
    padding-bottom: 20px;
    .setting-content {
      margin-left: 20px;
    }
    .mini-container {
      width: 100%;
      max-width: 500px;
    }
  }
</style>
