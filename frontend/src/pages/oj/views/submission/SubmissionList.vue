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
            <li>
              <el-switch v-model="formFilter.myself" active-text="" inactive-text="" @change="handleQueryChange">
                <template #active-action><span class="switch-label">My</span></template>
                <template #inactive-action><span class="switch-label">전체</span></template>
              </el-switch>
            </li>
            <li>
              <el-input v-model="formFilter.username" placeholder="작성자 검색" @keyup.enter="handleQueryChange" />
            </li>
            <li>
              <el-button type="primary" :icon="Refresh" @click="getSubmissions">새로고침</el-button>
            </li>
          </ul>
        </template>
        <el-table :data="submissions" v-loading="loadingTable" stripe>
          <el-table-column label="시간" align="center">
            <template #default="{ row }">{{ localtime(row.create_time) }}</template>
          </el-table-column>
          <el-table-column label="ID" align="center">
            <template #default="{ row }">
              <span v-if="row.show_link" class="link-text" @click="router.push('/status/' + row.id)">
                {{ row.id.slice(0, 12) }}
              </span>
              <span v-else>{{ row.id.slice(0, 12) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="상태" align="center">
            <template #default="{ row }">
              <el-tag :type="JUDGE_STATUS[row.result].type">
                {{ JUDGE_STATUS[row.result].label }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="문제" align="center">
            <template #default="{ row }">
              <span class="link-text" @click="goToProblem(row)">{{ row.problem }}</span>
            </template>
          </el-table-column>
          <el-table-column label="시간" align="center">
            <template #default="{ row }">{{ submissionTimeFormat(row.statistic_info.time_cost) }}</template>
          </el-table-column>
          <el-table-column label="메모리" align="center">
            <template #default="{ row }">{{ submissionMemoryFormat(row.statistic_info.memory_cost) }}</template>
          </el-table-column>
          <el-table-column label="언어" align="center" prop="language" />
          <el-table-column label="작성자" align="center">
            <template #default="{ row }">
              <a class="link-text truncate" @click="router.push({ name: 'user-home', query: { username: row.username } })">
                {{ row.username }}
              </a>
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

const formFilter = reactive({ myself: false, result: '', username: '' })
const loadingTable = ref(false)
const submissions = ref([])
const total = ref(30)
const limit = 12
const page = ref(1)
const contestID = ref('')
const problemID = ref('')
const routeName = ref('')

// Filter out submitting (9) and duplicate TLE (2)
const judgeStatusFiltered = computed(() => {
  const filtered = { ...JUDGE_STATUS }
  delete filtered['9']
  delete filtered['2']
  return filtered
})

const title = computed(() => {
  if (!contestID.value) return '상태'
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
  init()
})

watch(() => route.fullPath, (newVal, oldVal) => {
  if (newVal !== oldVal) init()
})

watch(() => userStore.isAuthenticated, () => {
  init()
})
</script>

<style scoped lang="less">
  .switch-label {
    font-size: 11px;
  }

  .link-text {
    color: #57a3f3;
    cursor: pointer;
  }

  .truncate {
    display: inline-block;
    max-width: 150px;
  }

  .flex-container {
    #main {
      flex: auto;
      margin-right: 18px;
      .filter {
        margin-right: -10px;
      }
    }
  }
</style>
