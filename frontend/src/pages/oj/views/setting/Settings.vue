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
                      <p class="text">change avatar</p>
                    </div>
                  </a>
                </div>
              </div>
            </div>

            <el-menu-item index="/setting/profile">{{ t('m.Profile') }}</el-menu-item>
            <el-menu-item index="/setting/account">{{ t('m.Account') }}</el-menu-item>
            <el-menu-item index="/setting/security">{{ t('m.Security') }}</el-menu-item>
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
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Camera } from '@element-plus/icons-vue'
import { useUserStore } from '@/store/user'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const activeName = computed(() => route.path)

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
