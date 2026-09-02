<template>
  <div class="container">
    <div class="avatar-container">
      <img class="avatar" :src="profile.avatar" />
    </div>
    <el-card :body-style="{ padding: '100px' }">
      <div v-if="profile.user">
        <p class="user-info">
          <span v-if="profile.user" class="emphasis">{{ profile.user.username }}</span>
        </p>
        <hr id="split" />

        <div class="flex-container">
          <div class="left">
            <p>해결</p>
            <p class="emphasis">{{ profile.accepted_number }}</p>
          </div>
          <div class="middle">
            <p>제출</p>
            <p class="emphasis">{{ profile.submission_number }}</p>
          </div>
          <div class="right">
            <p>점수</p>
            <p class="emphasis">{{ profile.total_score }}</p>
          </div>
        </div>

        <div id="problems">
          <div v-if="problems.length">해결한 문제 목록</div>
          <p v-else>아직 문제를 해결하지 않은 게으른 사람입니다.</p>
          <div class="btns">
            <div class="problem-btn" v-for="problemID of problems" :key="problemID">
              <el-button @click="goProblem(problemID)">{{ problemID }}</el-button>
            </div>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@oj/api'
import { useAppStore } from '@/store/app'
const route = useRoute()
const router = useRouter()
const appStore = useAppStore()

const username = ref('')
const profile = ref({})
const problems = ref([])

function getSolvedProblems () {
  const ACMProblems = profile.value.acm_problems_status?.problems || {}
  const OIProblems = profile.value.oi_problems_status?.problems || {}
  // 키가 곧 문제 번호다(pk). 숫자 정렬을 해야 9 가 10 보다 앞에 온다.
  const ACProblems = []
  for (const p of [ACMProblems, OIProblems]) {
    Object.keys(p).forEach((problemID) => {
      if (p[problemID].status === 0) ACProblems.push(problemID)
    })
  }
  ACProblems.sort((a, b) => Number(a) - Number(b))
  problems.value = ACProblems
}

async function init () {
  username.value = route.query.username || ''
  const res = await api.getUserInfo(username.value)
  appStore.changeDomTitle(res.data.data.user.username)
  profile.value = res.data.data
  getSolvedProblems()
}

function goProblem (problemID) {
  router.push({ name: 'problem-details', params: { problemID } })
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
  }
</style>
