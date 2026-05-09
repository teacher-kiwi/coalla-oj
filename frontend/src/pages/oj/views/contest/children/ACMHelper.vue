<template>
  <Panel shadow>
    <template #title>{{ t('m.ACM_Helper') }}</template>
    <template #extra>
      <ul class="filter">
        <li>
          {{ t('m.Auto_Refresh') }} (10s)
          <el-switch class="auto-refresh-switch" @change="handleAutoRefreshToggle" />
        </li>
        <li>
          <el-button type="primary" @click="getACInfo">{{ t('m.Refresh') }}</el-button>
        </li>
      </ul>
    </template>

    <el-table :data="pagedAcInfo" v-loading="loadingTable" stripe>
      <el-table-column :label="t('m.AC_Time')" prop="ac_time" />
      <el-table-column :label="t('m.ProblemID')" align="center" prop="problem_display_id" />
      <el-table-column :label="t('m.First_Blood')" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.ac_info.is_first_ac" type="danger">{{ t('m.First_Blood') }}</el-tag>
          <span v-else>----</span>
        </template>
      </el-table-column>
      <el-table-column :label="t('m.Username')" align="center">
        <template #default="{ row }">
          <a class="link-text truncate"
             @click="router.push({ name: 'contest-submission-list', query: { username: row.username } })">
            {{ row.username }}
          </a>
        </template>
      </el-table-column>
      <el-table-column :label="t('m.RealName')" align="center">
        <template #default="{ row }">
          <span class="truncate">{{ row.real_name }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="t('m.Status')" align="center">
        <template #default="{ row }">
          <el-tag :type="row.checked ? 'success' : 'warning'">
            {{ row.checked ? t('m.Checked') : t('m.Not_Checked') }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="t('m.Option')" align="center" width="100">
        <template #default="{ row }">
          <el-button size="small" :disabled="row.checked" @click="updateCheckedStatus(row)">
            {{ t('m.Check_It') }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <Pagination :total="totalCount" :page-size="limit" :current="page"
                @on-change="handlePage" :show-sizer="true"
                @on-page-size-change="handlePageSizeChange" />
  </Panel>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import Pagination from '@oj/components/Pagination.vue'
import api from '@oj/api'
import { useContestStore } from '@/store/contest'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const contestStore = useContestStore()

const page = ref(1)
const totalCount = ref(0)
const loadingTable = ref(false)
const acInfo = ref([])
const pagedAcInfo = ref([])
const problemsMap = ref({})
let contestID = ''
let refreshFunc = null

const contest = computed(() => contestStore.contest)
const contestProblems = computed(() => contestStore.contestProblems)
const limit = computed({
  get: () => contestStore.rankLimit,
  set: (value) => contestStore.changeRankLimit(value)
})

function mapProblemDisplayID () {
  const map = {}
  contestProblems.value.forEach(ele => {
    map[ele.id] = ele._id
  })
  problemsMap.value = map
}

function getACInfo () {
  loadingTable.value = true
  const params = { contest_id: route.params.contestID }
  api.getACMACInfo(params).then(res => {
    loadingTable.value = false
    const data = res.data.data
    totalCount.value = data.length
    acInfo.value = data
    handlePage(1)
  }).catch(() => {
    loadingTable.value = false
  })
}

function updateCheckedStatus (row) {
  const data = {
    rank_id: row.id,
    contest_id: contestID,
    problem_id: row.problem_id,
    checked: true
  }
  api.updateACInfoCheckedStatus(data).then(() => {
    ElMessage.success('Succeeded')
    getACInfo()
  }).catch(() => {})
}

function handleAutoRefreshToggle (value) {
  if (value) {
    refreshFunc = setInterval(() => {
      page.value = 1
      getACInfo()
    }, 10000)
  } else {
    clearInterval(refreshFunc)
  }
}

function handlePage (p = 1) {
  if (p !== 1) page.value = p
  if (p !== 1) loadingTable.value = true
  const pageInfo = acInfo.value.slice((page.value - 1) * limit.value, page.value * limit.value)
  for (const v of pageInfo) {
    if (v.init) continue
    v.init = true
    v.problem_display_id = problemsMap.value[v.problem_id]
    v.ac_time = dayjs(contest.value.start_time).add(v.ac_info.ac_time, 'seconds').local().format('YYYY-M-D  HH:mm:ss')
  }
  pagedAcInfo.value = pageInfo
  loadingTable.value = false
}

function handlePageSizeChange () {
  handlePage(1)
}

onMounted(() => {
  contestID = route.params.contestID
  if (contestProblems.value.length === 0) {
    contestStore.getContestProblems(contestID).then(() => {
      mapProblemDisplayID()
      getACInfo()
    })
  } else {
    mapProblemDisplayID()
    getACInfo()
  }
})

onBeforeUnmount(() => {
  clearInterval(refreshFunc)
})
</script>

<style scoped lang="less">
  .auto-refresh-switch {
    margin-left: 5px;
  }

  .link-text {
    color: #57a3f3;
    cursor: pointer;
  }

  .truncate {
    display: inline-block;
    max-width: 150px;
  }
</style>
