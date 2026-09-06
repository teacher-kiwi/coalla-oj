<template>
  <div class="flex-container">
    <div id="main">
      <Panel shadow>
        <template #title>{{ title }}</template>
        <template #extra>
          <ul class="filter">
            <li>
              <el-dropdown @command="handleResultChange">
                <span class="el-dropdown-link">
                  {{ status }}
                  <el-icon><ArrowDown /></el-icon>
                </span>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="">전체</el-dropdown-item>
                    <el-dropdown-item v-for="s in Object.keys(judgeStatusFiltered)" :key="s" :command="s">
                      {{ JUDGE_STATUS[s].label }}
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </li>
            <li class="switch-filter">
              <span class="switch-label">내 제출</span>
              <el-switch v-model="formFilter.myself" @change="handleQueryChange" />
            </li>
            <li v-if="userStore.isTeacher && !contestID" class="switch-filter">
              <span class="switch-label">내 학생</span>
              <el-switch v-model="formFilter.myStudents" @change="handleQueryChange" />
            </li>
            <li>
              <el-input v-model="formFilter.username" placeholder="작성자 검색" @keyup.enter="handleQueryChange" />
            </li>
            <li>
              <el-button type="primary" :icon="Refresh" @click="getSubmissions">새로고침</el-button>
            </li>
          </ul>
        </template>
        <el-table :key="rejudgeColumnVisible" :data="submissions" v-loading="loadingTable" stripe>
          <el-table-column label="제출 시각" align="center" width="180" class-name="value-cell">
            <template #default="{ row }">{{ localtime(row.create_time) }}</template>
          </el-table-column>
          <el-table-column label="ID" align="center" width="130">
            <template #default="{ row }">
              <span v-if="row.show_link" class="link-text submission-id"
                    @click="router.push('/status/' + row.id)">
                {{ row.id.slice(0, 12) }}
              </span>
              <span v-else class="submission-id">{{ row.id.slice(0, 12) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="상태" align="center" width="120">
            <template #default="{ row }">
              <el-tag :type="JUDGE_STATUS[row.result].type">
                {{ JUDGE_STATUS[row.result].label }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="문제" align="center">
            <template #default="{ row }">
              <!-- 번호(row.problem)는 주소를 만드는 데 쓰고, 화면에는 제목을 보여준다 -->
              <span class="link-text" @click="goToProblem(row)">{{ row.problem_title }}</span>
            </template>
          </el-table-column>
          <el-table-column label="실행 시간" align="center" width="100" class-name="value-cell">
            <template #default="{ row }">{{ submissionTimeFormat(row.statistic_info.time_cost) }}</template>
          </el-table-column>
          <el-table-column label="메모리" align="center" width="100" class-name="value-cell">
            <template #default="{ row }">{{ submissionMemoryFormat(row.statistic_info.memory_cost) }}</template>
          </el-table-column>
          <el-table-column label="언어" align="center" prop="language" width="120" />
          <el-table-column label="작성자" align="center" width="200">
            <template #default="{ row }">
              <UserLabel :username="row.username" :nickname="row.nickname" />
            </template>
          </el-table-column>
          <el-table-column v-if="rejudgeColumnVisible" label="옵션" align="center" width="90">
            <template #default="{ row, $index }">
              <el-button type="primary" size="small" :loading="row.loading" @click="handleRejudge(row.id, $index)">
                재채점
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        <Pagination :total="total" :page-size="limit" :current="page" @on-change="onPageChange" />
      </Panel>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import UserLabel from '@oj/components/UserLabel.vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowDown, Refresh } from '@element-plus/icons-vue'
import api from '@oj/api'
import { JUDGE_STATUS, USER_TYPE } from '@/utils/constants'
import utils from '@/utils/utils'
import time from '@/utils/time'
import Pagination from '@oj/components/Pagination.vue'
import { useUserStore } from '@/store/user'

const { submissionTimeFormat, submissionMemoryFormat } = utils
const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const formFilter = reactive({ myself: false, myStudents: false, result: '', username: '' })
const loadingTable = ref(false)
const submissions = ref([])
const total = ref(30)
const limit = 12
const page = ref(1)
const contestID = ref('')
const problemID = ref('')
const routeName = ref('')

// 제출 중(9)과 중복되는 TLE(2)는 목록에서 뺀다
const judgeStatusFiltered = computed(() => {
  const filtered = { ...JUDGE_STATUS }
  delete filtered['9']
  delete filtered['2']
  return filtered
})

const title = computed(() => {
  if (!contestID.value) return '제출 현황'
  if (problemID.value) return '문제별 제출'
  return '제출'
})

const status = computed(() => {
  return formFilter.result === '' ? '상태' : JUDGE_STATUS[formFilter.result].label
})

const rejudgeColumnVisible = computed(() => {
  return !contestID.value && userStore.user.admin_type === USER_TYPE.SUPER_ADMIN
})

function localtime (val) {
  return time.utcToLocal(val)
}

function buildQuery () {
  return {
    myself: formFilter.myself === true ? '1' : '0',
    my_students: formFilter.myStudents === true ? '1' : '0',
    result: formFilter.result,
    username: formFilter.username,
    page: page.value
  }
}

function init () {
  contestID.value = route.params.contestID || ''
  const query = route.query
  problemID.value = query.problemID || ''
  formFilter.myself = query.myself === '1'
  formFilter.myStudents = query.my_students === '1'
  formFilter.result = query.result || ''
  formFilter.username = query.username || ''
  page.value = parseInt(query.page) || 1
  if (page.value < 1) page.value = 1
  routeName.value = route.name
  getSubmissions()
}

function getSubmissions () {
  const params = buildQuery()
  params.contest_id = contestID.value
  params.problem_id = problemID.value
  const offset = (page.value - 1) * limit
  const func = contestID.value ? 'getContestSubmissionList' : 'getSubmissionList'
  loadingTable.value = true
  api[func](offset, limit, params).then(res => {
    const data = res.data.data
    for (const v of data.results) {
      v.loading = false
    }
    loadingTable.value = false
    submissions.value = data.results
    total.value = data.total
  }).catch(() => {
    loadingTable.value = false
  })
}

function changeRoute () {
  const query = utils.filterEmptyValue(buildQuery())
  query.contestID = contestID.value
  query.problemID = problemID.value
  const rName = query.contestID ? 'contest-submission-list' : 'submission-list'
  router.push({ name: rName, query: utils.filterEmptyValue(query) })
}

function goToProblem (row) {
  if (contestID.value) {
    router.push({ name: 'contest-problem-details', params: { problemID: row.problem, contestID: contestID.value } })
  } else {
    router.push({ name: 'problem-details', params: { problemID: row.problem } })
  }
}

function onPageChange (newPage) {
  page.value = newPage
  changeRoute()
}

function handleResultChange (statusVal) {
  page.value = 1
  formFilter.result = statusVal
  changeRoute()
}

function handleQueryChange () {
  page.value = 1
  changeRoute()
}

function handleRejudge (id, index) {
  submissions.value[index].loading = true
  api.submissionRejudge(id).then(() => {
    submissions.value[index].loading = false
    ElMessage.success('완료되었습니다')
    getSubmissions()
  }, () => {
    submissions.value[index].loading = false
  })
}

onMounted(() => {
  userStore.ensureProfile()
})

watch(() => route.fullPath, (newVal, oldVal) => {
  if (newVal !== oldVal) init()
})

// 로그인 여부가 확정된 뒤에 한 번, 그리고 로그인/로그아웃할 때마다 다시 부른다.
// 두 값을 한 감시자에 묶어 둘이 같이 바뀌는 최초 로드에서도 한 번만 실행되게 한다.
watch(() => [userStore.profileReady, userStore.user.id], ([ready]) => {
  if (ready) init()
}, { immediate: true })
</script>

<style scoped lang="less">
  // 스위치 옆에 두는 이름. 예전에는 el-switch 의 action 슬롯에 넣었는데,
  // 그 자리는 지름 16px 짜리 동그란 손잡이 안이라 한글이 줄바꿈되며 튀어나왔다.
  .switch-filter {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }

  .switch-label {
    font-size: 13px;
    color: #606266;
    white-space: nowrap;
  }

  // "홍길동김(학생00000000)" 까지는 한 줄에 들어가야 한다(한국 이름은 보통 3자,
  // 드물게 4자다). 그보다 길면 줄이 바뀐다.
  // 날짜·시간·메모리처럼 길이가 정해진 값. 폭을 넉넉히 줬지만 글꼴이 비례폭이라
  // 어림이 빗나갈 수 있어, 넘치더라도 줄은 바뀌지 않게 한다.
  :deep(.value-cell) {
    white-space: nowrap;
  }

  // 제출 ID 는 12자리 16진수다. 본문 글꼴은 고정폭이 아니라 글자 조합에 따라
  // 폭이 달라져(f 는 좁고 8·d 는 넓다) 어떤 ID 만 줄이 바뀌었다.
  // 고정폭 글꼴을 쓰면 어느 ID 든 폭이 같아 줄도 세로로 가지런히 맞는다.
  .submission-id {
    font-family: Menlo, Monaco, Consolas, "Courier New", monospace;
    font-size: 13px;
    white-space: nowrap;
  }

  .truncate {
    display: inline-block;
    max-width: 170px;
  }

  .flex-container {
    #main {
      flex: auto;
      // flex 항목의 기본 min-width 는 auto 라 "내용의 최소 폭" 아래로 줄지 않는다.
      // 표는 컬럼 폭이 픽셀로 정해져 있어 그 최소 폭이 커지고, 그러면 창을 줄여도
      // 이 칸이 버티며 표도 줄지 않아 화면 전체에 가로 스크롤이 생겼다.
      // (넓힐 때는 늘어나므로 "늘리면 되고 줄이면 안 되는" 모양이 된다)
      // 0 으로 풀면 칸이 먼저 줄고, 표는 자기 안에서 가로 스크롤을 만든다.
      min-width: 0;
      .filter {
        margin-right: -10px;
      }
    }
  }
</style>
