<template>
  <Panel shadow>
    <template #title>{{ contest.title }}</template>
    <template #extra>
      <ScreenFull class="screen-full" />
      <el-popover trigger="hover" placement="left-start">
        <template #reference>
          <el-icon :size="20" class="setting-icon"><Setting /></el-icon>
        </template>
        <div id="switches">
          <p>
            <span>{{ t('m.Menu') }}</span>
            <el-switch v-model="showMenu" />
            <span>{{ t('m.Chart') }}</span>
            <el-switch v-model="showChart" />
          </p>
          <p>
            <span>{{ t('m.Auto_Refresh') }}(10s)</span>
            <el-switch :disabled="refreshDisabled" @change="onAutoRefresh" />
          </p>
          <template v-if="isContestAdmin">
            <p>
              <span>{{ t('m.RealName') }}</span>
              <el-switch v-model="showRealName" />
            </p>
            <p>
              <span>{{ t('m.Force_Update') }}</span>
              <el-switch :disabled="refreshDisabled" v-model="forceUpdate" />
            </p>
          </template>
          <p>
            <el-button type="primary" size="small" @click="downloadRankCSV">{{ t('m.download_csv') }}</el-button>
          </p>
        </div>
      </el-popover>
    </template>

    <div v-show="showChart" class="echarts">
      <VChart ref="chart" :option="options" :loading="chartLoading" autoresize />
    </div>

    <el-table :data="dataRank" height="600" stripe :cell-class-name="cellClassName">
      <el-table-column align="center" width="50">
        <template #default="{ $index }">{{ $index + (page - 1) * limit + 1 }}</template>
      </el-table-column>
      <el-table-column :label="t('m.User_User')" align="center" width="150">
        <template #default="{ row }">
          <a class="link-text truncate"
             @click="router.push({ name: 'user-home', query: { username: row.user.username } })">
            {{ row.user.username }}
          </a>
        </template>
      </el-table-column>
      <el-table-column v-if="showRealName" label="RealName" align="center" width="150">
        <template #default="{ row }">{{ row.user.real_name }}</template>
      </el-table-column>
      <el-table-column :label="'AC / ' + t('m.Total')" align="center" width="100">
        <template #default="{ row }">
          <span>{{ row.accepted_number }} / </span>
          <a class="link-text" @click="router.push({ name: 'contest-submission-list', query: { username: row.user.username } })">
            {{ row.submission_number }}
          </a>
        </template>
      </el-table-column>
      <el-table-column :label="t('m.TotalTime')" align="center" width="100">
        <template #default="{ row }">{{ parseTotalTime(row.total_time) }}</template>
      </el-table-column>
      <el-table-column v-for="prob in contestProblems" :key="prob.id" align="center"
                       :column-key="String(prob.id)"
                       :width="contestProblems.length > 15 ? 80 : undefined">
        <template #header>
          <a class="emphasis link-text"
             @click="router.push({ name: 'contest-problem-details', params: { contestID, problemID: prob._id } })">
            {{ prob._id }}
          </a>
        </template>
        <template #default="{ row }">
          <template v-if="row[prob.id]">
            <span v-if="row[prob.id].is_ac">{{ row[prob.id].ac_time }}</span>
            <p v-if="row[prob.id].error_number !== 0" class="error-count">(-{{ row[prob.id].error_number }})</p>
          </template>
        </template>
      </el-table-column>
    </el-table>

    <Pagination :total="total" :page-size="limit" :current="page"
                @on-change="onPageChange" :show-sizer="true"
                @on-page-size-change="onPageSizeChange" />
  </Panel>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import dayjs from 'dayjs'
import duration from 'dayjs/plugin/duration'
import { Setting } from '@element-plus/icons-vue'
import Pagination from '@oj/components/Pagination.vue'
import ScreenFull from '@admin/components/ScreenFull.vue'
import { useContestRank } from './contestRankMixin'
import time from '@/utils/time'
import utils from '@/utils/utils'

dayjs.extend(duration)

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const {
  contest, contestProblems, isContestAdmin,
  showChart, showMenu, showRealName, forceUpdate, limit, refreshDisabled,
  chartLoading, getContestRankData, handleAutoRefresh, getContestProblems
} = useContestRank()

const total = ref(0)
const page = ref(1)
const contestID = ref('')
const chart = ref(null)
const dataRank = ref([])
const options = ref({
  title: { text: t('m.Top_10_Teams'), left: 'center' },
  dataZoom: [{ type: 'inside', filterMode: 'none', xAxisIndex: [0], start: 0, end: 100 }],
  toolbox: {
    show: true,
    feature: { saveAsImage: { show: true, title: t('m.save_as_image') } },
    right: '5%'
  },
  tooltip: { trigger: 'axis', axisPointer: { type: 'cross', axis: 'x' } },
  legend: {
    orient: 'vertical', y: 'center', right: 0, data: [],
    formatter: (value) => utils.breakLongWords(value, 16),
    textStyle: { fontSize: 12 }
  },
  grid: { x: 80, x2: 200 },
  xAxis: [{ type: 'time', splitLine: false, axisPointer: { show: true, snap: true } }],
  yAxis: [{ type: 'category', boundaryGap: false, data: [0] }],
  series: []
})

function applyToChart (rankData) {
  const [users, seriesData] = [[], []]
  rankData.forEach(rank => {
    users.push(rank.user.username)
    const info = rank.submission_info
    const timeData = []
    Object.keys(info).forEach(problemID => {
      if (info[problemID].is_ac) timeData.push(info[problemID].ac_time)
    })
    timeData.sort((a, b) => a - b)
    const data = [[contest.value.start_time, 0]]
    for (const [index, value] of timeData.entries()) {
      const realTime = dayjs(contest.value.start_time).add(value, 'seconds').format()
      data.push([realTime, index + 1])
    }
    seriesData.push({ name: rank.user.username, type: 'line', data })
  })
  options.value = { ...options.value, legend: { ...options.value.legend, data: users }, series: seriesData }
}

function applyToTable (data) {
  const dataRankArr = JSON.parse(JSON.stringify(data))
  dataRankArr.forEach((rank, i) => {
    const info = rank.submission_info
    Object.keys(info).forEach(problemID => {
      dataRankArr[i][problemID] = info[problemID]
      dataRankArr[i][problemID].ac_time = time.secondFormat(dataRankArr[i][problemID].ac_time)
    })
  })
  dataRank.value = dataRankArr
}

function cellClassName ({ row, column }) {
  const probId = column.columnKey
  if (!probId || !row[probId]) return ''
  if (row[probId].is_first_ac) return 'first-ac'
  if (row[probId].is_ac) return 'ac'
  return 'wa'
}

function getData (p = 1) {
  getContestRankData(p, applyToChart, applyToTable).then(t => {
    total.value = t
  })
}

function onPageChange (newPage) {
  page.value = newPage
  getData(newPage)
}

function onPageSizeChange () {
  getData(1)
}

function onAutoRefresh (status) {
  handleAutoRefresh(status, page.value, getData)
}

function parseTotalTime (totalTime) {
  const m = dayjs.duration(totalTime, 's')
  return [Math.floor(m.asHours()), m.minutes(), m.seconds()].join(':')
}

function downloadRankCSV () {
  utils.downloadFile(`contest_rank?download_csv=1&contest_id=${route.params.contestID}&force_refrash=${forceUpdate.value ? '1' : '0'}`)
}

onMounted(() => {
  contestID.value = route.params.contestID
  getData(1)
  if (contestProblems.value.length === 0) {
    getContestProblems(contestID.value).then(res => {
      if (res?.data?.data) {
        const category = []
        for (let i = 0; i <= res.data.data.length; ++i) category.push(i)
        options.value.yAxis[0].data = category
      }
    })
  } else {
    const category = []
    for (let i = 0; i <= contestProblems.value.length; ++i) category.push(i)
    options.value.yAxis[0].data = category
  }
})
</script>

<style scoped lang="less">
  .echarts {
    margin: 20px auto;
    height: 400px;
    width: 98%;
  }

  .screen-full {
    margin-right: 8px;
  }

  .setting-icon {
    cursor: pointer;
  }

  .link-text {
    color: #57a3f3;
    cursor: pointer;
  }

  .truncate {
    display: inline-block;
    max-width: 150px;
  }

  .error-count {
    margin: 0;
  }

  :deep(td.first-ac) {
    background: #33cc99 !important;
    color: #fff;
    text-align: center;
  }
  :deep(td.ac) {
    background: #dff0d8 !important;
    text-align: center;
  }
  :deep(td.wa) {
    background: #f2dede !important;
    text-align: center;
  }

  #switches {
    p {
      margin-top: 5px;
      &:first-child {
        margin-top: 0;
      }
      span {
        margin-left: 8px;
      }
    }
  }
</style>
