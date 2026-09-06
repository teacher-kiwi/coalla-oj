<template>
  <div class="flex-container">
    <div id="contest-main">
      <router-view v-slot="{ Component }">
        <transition name="fadeInUp">
          <component :is="Component" />
        </transition>
      </router-view>
      <div class="flex-container" v-if="route_name === 'contest-details'">
        <div id="contest-desc">
          <Panel :padding="20" shadow>
            <template #title>{{ contest.title }}</template>
            <template #extra>
              <el-tag :type="countdownType">
                <span id="countdown">{{ countdown }}</span>
              </el-tag>
            </template>
            <Markdown :source="contest.description" />
            <div v-if="passwordFormVisible" class="contest-password">
              <el-input v-model="contestPassword" type="password"
                        placeholder="대회 비밀번호" class="contest-password-input"
                        @keyup.enter="checkPassword" />
              <el-button type="primary" @click="checkPassword">입장</el-button>
            </div>
          </Panel>
          <el-table :data="contestTable" class="contest-info-table">
            <el-table-column label="시작 시간">
              <template #default="{ row }">{{ localtime(row.start_time) }}</template>
            </el-table-column>
            <el-table-column label="종료 시간">
              <template #default="{ row }">{{ localtime(row.end_time) }}</template>
            </el-table-column>
            <el-table-column label="대회 유형">
              <template #default="{ row }">{{ row.contest_type ? CONTEST_TYPE_LABEL[row.contest_type] : '' }}</template>
            </el-table-column>
            <el-table-column label="규칙">
              <template #default="{ row }">{{ row.rule_type ? RULE_TYPE_LABEL[row.rule_type] : '' }}</template>
            </el-table-column>
            <el-table-column label="생성자">
              <template #default="{ row }">{{ row.created_by.username }}</template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </div>

    <div v-show="showMenu" id="contest-menu">
      <VerticalMenu @on-click="handleRoute">
        <VerticalMenuItem :route="{ name: 'contest-details', params: { contestID } }">
          <el-icon><House /></el-icon>
          개요
        </VerticalMenuItem>
        <VerticalMenuItem :disabled="contestMenuDisabled"
                          :route="{ name: 'contest-announcement-list', params: { contestID } }">
          <el-icon><ChatDotRound /></el-icon>
          공지
        </VerticalMenuItem>
        <VerticalMenuItem :disabled="contestMenuDisabled"
                          :route="{ name: 'contest-problem-list', params: { contestID } }">
          <el-icon><PictureFilled /></el-icon>
          문제
        </VerticalMenuItem>
        <VerticalMenuItem v-if="OIContestRealTimePermission"
                          :disabled="contestMenuDisabled"
                          :route="{ name: 'contest-submission-list' }">
          <el-icon><List /></el-icon>
          제출
        </VerticalMenuItem>
        <VerticalMenuItem v-if="OIContestRealTimePermission"
                          :disabled="contestMenuDisabled"
                          :route="{ name: 'contest-rank', params: { contestID } }">
          <el-icon><TrendCharts /></el-icon>
          순위
        </VerticalMenuItem>
        <VerticalMenuItem v-if="showAdminHelper"
                          :route="{ name: 'acm-helper', params: { contestID } }">
          <el-icon><MagicStick /></el-icon>
          관리자 도우미
        </VerticalMenuItem>
        <!-- 학급 대회를 연 교사에게. 관리자 도우미는 /api/admin/* 을 쓰므로
             교사 권한으로는 열리지 않는다(눌러도 로그인하라는 응답만 온다). -->
        <VerticalMenuItem v-if="showClassContestEdit"
                          :route="{ name: 'teacher-contest-detail', params: { contestId: contestID } }">
          <el-icon><Edit /></el-icon>
          대회 수정
        </VerticalMenuItem>
      </VerticalMenu>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import Markdown from '@oj/components/Markdown.vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { House, ChatDotRound, PictureFilled, List, TrendCharts, MagicStick, Edit } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import api from '@oj/api'
import time from '@/utils/time'
import { CONTEST_STATUS_REVERSE, RULE_TYPE_LABEL, CONTEST_TYPE_LABEL } from '@/utils/constants'
import VerticalMenu from '@oj/components/verticalMenu/verticalMenu.vue'
import VerticalMenuItem from '@oj/components/verticalMenu/verticalMenu-item.vue'
import { useContestStore } from '@/store/contest'
import { useUserStore } from '@/store/user'
import { useAppStore } from '@/store/app'

const route = useRoute()
const router = useRouter()
const contestStore = useContestStore()
const userStore = useUserStore()
const appStore = useAppStore()

const route_name = ref('')
const contestID = ref('')
const contestPassword = ref('')
let timer = null

const contest = computed(() => contestStore.contest)
const contestTable = computed(() => [contestStore.contest])
const showMenu = computed(() => contestStore.itemVisible.menu)
const contestMenuDisabled = computed(() => contestStore.contestMenuDisabled)
const contestRuleType = computed(() => contestStore.contestRuleType)
const contestStatusVal = computed(() => contestStore.contestStatus)
const countdown = computed(() => contestStore.countdown)
const isContestAdmin = computed(() => contestStore.isContestAdmin)
const OIContestRealTimePermission = computed(() => contestStore.OIContestRealTimePermission)
const passwordFormVisible = computed(() => contestStore.passwordFormVisible)

const countdownType = computed(() =>
  CONTEST_STATUS_REVERSE[contestStatusVal.value]?.tag || 'warning')

// 관리자 도우미는 /api/admin/* 이라 관리자만 쓸 수 있다. 학급 대회를 연 교사는
// isContestAdmin 이지만 관리자 권한이 없어, 메뉴가 보이면 눌렀을 때 실패한다.
const showAdminHelper = computed(() =>
  isContestAdmin.value && contestRuleType.value === 'ACM' &&
  !contest.value.is_class_contest && userStore.isAdminRole)
// 학급 대회를 연 교사에게는 대신 교사용 관리 화면으로 보낸다
const showClassContestEdit = computed(() =>
  isContestAdmin.value && contest.value.is_class_contest && userStore.isTeacher)

function localtime (val) {
  return time.utcToLocal(val)
}

function handleRoute (routeObj) {
  router.push(routeObj)
}

function checkPassword () {
  if (contestPassword.value === '') {
    ElMessage.error('비밀번호를 입력하세요')
    return
  }
  api.checkContestPassword(contestID.value, contestPassword.value).then(() => {
    ElMessage.success('완료되었습니다')
    contestStore.access = true
  }, () => {})
}

onMounted(() => {
  contestID.value = route.params.contestID
  route_name.value = route.name
  contestStore.getContest(contestID.value).then(res => {
    appStore.changeDomTitle(res.data.data.title)
    const data = res.data.data
    const endTime = dayjs(data.end_time)
    if (endTime.isAfter(dayjs(data.now))) {
      timer = setInterval(() => {
        contestStore.updateNow()
      }, 1000)
    }
  })
})

watch(() => route.fullPath, () => {
  route_name.value = route.name
  contestID.value = route.params.contestID
  appStore.changeDomTitle(contest.value.title)
})

onBeforeUnmount(() => {
  clearInterval(timer)
  contestStore.clearContest()
})
</script>

<style scoped lang="less">
  pre {
    display: inline-block;
  }

  #countdown {
    font-size: 16px;
  }

  .contest-info-table {
    margin-bottom: 40px;
  }

  .flex-container {
    #contest-main {
      flex: 1 1;
      // flex 항목의 기본 min-width 는 auto 라 "내용의 최소 폭" 아래로 줄지 않는다.
      // 안에 표(대회 정보·순위)와 마크다운이 들어와 그 최소 폭이 커지면, 창을 줄여도
      // 이 칸이 버티며 카드까지 함께 화면을 넘긴다.
      // width: 0 은 이것을 막지 못한다. flex-basis 는 이미 0 이고 min-width 가 따로
      // 걸리기 때문이다. 풀어야 하는 것은 min-width 다.
      // (submission/SubmissionList.vue 에 같은 설명이 있다)
      min-width: 0;
      #contest-desc {
        flex: auto;
        min-width: 0;
      }
    }
    #contest-menu {
      flex: none;
      width: 210px;
      margin-left: 20px;
    }
    .contest-password {
      margin-top: 20px;
      margin-bottom: -10px;
      &-input {
        width: 200px;
        margin-right: 10px;
      }
    }
  }
</style>
