<template>
  <div class="container">
    <div class="avatar-container">
      <CharacterAvatar v-if="profile.user" :username="profile.user.username" mode="full"
                       :size="128" animate />
    </div>
    <el-card class="profile-card">
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
          <p v-else class="empty">아직 해결한 문제가 없습니다.</p>
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
import CharacterAvatar from '@oj/components/CharacterAvatar.vue'
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
  // 다른 화면과 같은 카드 폭 안에서 가운데에 둔다(예전에는 창의 75% 라 넓은 화면에서 휑했다)
  .container {
    position: relative;
    max-width: 860px;
    // 위쪽은 margin 이 아니라 padding 으로 띄운다. margin 이면 본문의 margin-top(80px)과
    // 겹쳐 하나로 합쳐지고, 위로 튀어나온 캐릭터 동그라미가 상단 메뉴 밑으로 숨는다.
    margin: 0 auto 40px;
    padding-top: 90px;
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
      top: 0;
      // 전신 도트(64칸)를 2배로 키워 동그란 배경 가운데에 세운다
      display: flex;
      align-items: flex-end;
      justify-content: center;
      width: 140px;
      height: 140px;
      border-radius: 50%;
      background: #eef4fb;
      box-shadow: 0 1px 3px rgba(0, 0, 0, .12);
    }
    .profile-card :deep(.el-card__body) {
      padding: 80px 48px 40px;
    }
    .user-info {
      margin-top: -10px;
    }
    .empty {
      color: #909399;
      font-size: 15px;
    }
    .emphasis {
      font-size: 20px;
      font-weight: 600;
    }
    #split {
      margin: 20px auto;
      width: 90%;
      border: none;
      border-top: 1px solid #ebeef5;
    }
    .flex-container {
      display: flex;
      margin-top: 30px;
      .left, .middle, .right { flex: 1 1; }
      .middle {
        border-left: 1px solid #ebeef5;
        border-right: 1px solid #ebeef5;
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
