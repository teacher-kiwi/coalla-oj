<template>
  <div class="container">
    <el-card :body-style="{ padding: 0 }">
      <div class="flex-container">
        <div class="menu">
          <el-menu :default-active="activeName" @select="goRoute" class="setting-menu">
            <div class="avatar-editor">
              <div class="avatar-container">
                <img class="avatar" :src="userStore.profile.avatar" />
                <div class="avatar-mask">
                  <a @click.stop="goRoute('/setting/profile')">
                    <div class="mask-content">
                      <el-icon :size="30"><Camera /></el-icon>
                      <p class="text">사진 변경</p>
                    </div>
                  </a>
                </div>
              </div>
            </div>

            <el-menu-item v-if="isStudent" index="/setting/password">비밀번호 변경</el-menu-item>
            <template v-else>
              <el-menu-item index="/setting/profile">프로필</el-menu-item>
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
import { Camera } from '@element-plus/icons-vue'
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
  @avatar-radius: 50%;

  .container {
    width: 90%;
    min-width: 800px;
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
      .avatar-editor {
        padding: 10% 22%;
        margin-bottom: 10px;
        .avatar-container {
          &:hover {
            .avatar-mask {
              opacity: .5;
            }
          }
          position: relative;
          .avatar {
            width: 100%;
            height: auto;
            max-width: 100%;
            display: block;
            border-radius: @avatar-radius;
            box-shadow: 0 0 1px 0;
          }
          .avatar-mask {
            transition: opacity .2s ease-in;
            z-index: 1;
            border-radius: @avatar-radius;
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: black;
            opacity: 0;
            .mask-content {
              position: absolute;
              top: 50%; left: 50%;
              z-index: 3;
              color: #fff;
              font-size: 16px;
              text-align: center;
              transform: translate(-50%, -50%);
              .text { white-space: nowrap; }
            }
          }
        }
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
      width: 500px;
    }
  }
</style>
