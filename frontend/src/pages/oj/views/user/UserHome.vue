<template>
  <div class="container">
    <div class="avatar-container">
      <img class="avatar" :src="profile.avatar" />
    </div>
    <el-card :body-style="{ padding: '100px' }">
      <div v-if="profile.user">
        <p class="user-info">
          <span v-if="profile.user" class="emphasis">{{ profile.user.username }}</span>
          <span v-if="profile.school">@{{ profile.school }}</span>
        </p>
        <p v-if="profile.mood">{{ profile.mood }}</p>
        <hr id="split" />

        <div class="flex-container">
          <div class="left">
            <p>{{ t('m.UserHomeSolved') }}</p>
            <p class="emphasis">{{ profile.accepted_number }}</p>
          </div>
          <div class="middle">
            <p>{{ t('m.UserHomeserSubmissions') }}</p>
            <p class="emphasis">{{ profile.submission_number }}</p>
          </div>
          <div class="right">
            <p>{{ t('m.UserHomeScore') }}</p>
            <p class="emphasis">{{ profile.total_score }}</p>
          </div>
        </div>

        <div id="problems">
          <div v-if="problems.length">
            {{ t('m.List_Solved_Problems') }}
            <el-popover v-if="refreshVisible" trigger="hover" placement="right-start">
              <template #reference>
                <el-icon><QuestionFilled /></el-icon>
              </template>
              <p>If you find the following problem id does not exist,<br /> try to click the button.</p>
              <el-button type="info" @click="freshProblemDisplayID">regenerate</el-button>
            </el-popover>
          </div>
          <p v-else>{{ t('m.UserHomeIntro') }}</p>
          <div class="btns">
            <div class="problem-btn" v-for="problemID of problems" :key="problemID">
              <el-button @click="goProblem(problemID)">{{ problemID }}</el-button>
            </div>
          </div>
        </div>

        <div id="icons">
          <a :href="profile.github"><el-icon :size="30"><Link /></el-icon></a>
          <a :href="'mailto:' + profile.user.email"><el-icon :size="30" class="icon"><Message /></el-icon></a>
          <a :href="profile.blog"><el-icon :size="30" class="icon"><Promotion /></el-icon></a>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { QuestionFilled, Link, Message, Promotion } from '@element-plus/icons-vue'
import time from '@/utils/time'
import api from '@oj/api'
import { useAppStore } from '@/store/app'
import { useUserStore } from '@/store/user'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const userStore = useUserStore()

const username = ref('')
const profile = ref({})
const problems = ref([])

const refreshVisible = computed(() => {
  if (!username.value) return true
  if (username.value && userStore.user.username === username.value) return true
  return false
})

function getSolvedProblems () {
  const ACMProblems = profile.value.acm_problems_status?.problems || {}
  const OIProblems = profile.value.oi_problems_status?.problems || {}
  const ACProblems = []
  for (const p of [ACMProblems, OIProblems]) {
    Object.keys(p).forEach((problemID) => {
      if (p[problemID].status === 0) ACProblems.push(p[problemID]._id)
    })
  }
  ACProblems.sort()
  problems.value = ACProblems
}

async function init () {
  username.value = route.query.username || ''
  const res = await api.getUserInfo(username.value)
  appStore.changeDomTitle(res.data.data.user.username)
  profile.value = res.data.data
  getSolvedProblems()
  const registerTime = time.utcToLocal(profile.value.user.create_time, 'YYYY-MM-D')
  // eslint-disable-next-line no-console
  console.log('The guy registered at ' + registerTime + '.')
}

function goProblem (problemID) {
  router.push({ name: 'problem-details', params: { problemID } })
}

function freshProblemDisplayID () {
  api.freshDisplayID().then(() => {
    ElMessage.success('Update successfully')
    init()
  })
}

onMounted(init)
watch(() => route.fullPath, init)
</script>

<style lang="less" scoped>
  .container {
    position: relative;
    width: 75%;
    margin: 170px auto;
    text-align: center;
    p {
      margin-top: 8px;
      margin-bottom: 8px;
    }
    .avatar-container {
      position: absolute;
      left: 50%;
      transform: translate(-50%);
      z-index: 1;
      top: -90px;
      .avatar {
        width: 140px;
        height: 140px;
        border-radius: 50%;
        box-shadow: 0 1px 1px 0;
      }
    }
    .user-info {
      margin-top: -10px;
    }
    .emphasis {
      font-size: 20px;
      font-weight: 600;
    }
    #split {
      margin: 20px auto;
      width: 90%;
    }
    .flex-container {
      display: flex;
      margin-top: 30px;
      .left, .middle, .right { flex: 1 1; }
      .middle {
        border-left: 1px solid #999;
        border-right: 1px solid #999;
      }
    }
    #problems {
      margin-top: 40px;
      padding-left: 30px;
      padding-right: 30px;
      font-size: 18px;
      .btns {
        margin-top: 15px;
        .problem-btn {
          display: inline-block;
          margin: 5px;
        }
      }
    }
    #icons {
      position: absolute;
      bottom: 20px;
      left: 50%;
      transform: translate(-50%);
      .icon {
        padding-left: 20px;
      }
    }
  }
</style>
