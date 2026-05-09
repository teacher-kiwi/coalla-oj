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
          <p v-if="isContestAdmin">
            <span>{{ t('m.RealName') }}</span>
            <el-switch v-model="showRealName" />
          </p>
          <p>
            <el-button type="primary" size="small" @click="downloadRankCSV">{{ t('m.download_csv') }}</el-button>
          </p>
        </div>
      </el-popover>
    </template>

    <div v-show="showChart" class="echarts">
      <VChart ref="chart" :option="options" :loading="chartLoading" autoresize />
    </div>

    <el-table :data="dataRank" stripe>
      <el-table-column align="center" width="60">
        <template #default="{ $index }">{{ $index + (page - 1) * limit + 1 }}</template>
      </el-table-column>
      <el-table-column :label="t('m.User_User')" align="center">
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
      <el-table-column :label="t('m.Total_Score')" align="center">
        <template #default="{ row }">
          <a class="link-text" @click="router.push({ name: 'contest-submission-list', query: { username: row.user.username } })">
            {{ row.total_score }}
          </a>
        </template>
      </el-table-column>
      <el-table-column v-for="prob in contestProblems" :key="prob.id" align="center">
        <template #header>
          <a class="emphasis link-text"
             @click="router.push({ name: 'contest-problem-details', params: { contestID, problemID: prob._id } })">
            {{ prob._id }}
          </a>
        </template>
        <template #default="{ row }">
          <span>{{ row[prob.id] }}</span>
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
import { Setting } from '@element-plus/icons-vue'
import Pagination from '@oj/components/Pagination.vue'
import ScreenFull from '@admin/components/ScreenFull.vue'
import { useContestRank } from './contestRankMixin'
import utils from '@/utils/utils'

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
  tooltip: { trigger: 'axis' },
  toolbox: {
    show: true,
    feature: {
      dataView: { show: true, readOnly: true },
      magicType: { show: true, type: ['line', 'bar'] },
      saveAsImage: { show: true }
    },
    right: '10%'
  },
  calculable: true,
  xAxis: [{
    type: 'category', data: ['root'], boundaryGap: true,
    axisLabel: {
      interval: 0, showMinLabel: true, showMaxLabel: true, align: 'center',
      formatter: (value) => utils.breakLongWords(value, 14)
    },
    axisTick: { alignWithLabel: true }
  }],
  yAxis: [{ type: 'value' }],
  series: [{
    name: t('m.Score'), type: 'bar', barMaxWidth: '80', data: [0],
    markPoint: { data: [{ type: 'max', name: 'max' }] }
  }]
})

function applyToChart (rankData) {
  const [usernames, scores] = [[], []]
  rankData.forEach(ele => {
    usernames.push(ele.user.username)
    scores.push(ele.total_score)
  })
  options.value.xAxis[0].data = usernames
  options.value.series[0].data = scores
  options.value = { ...options.value }
}

function applyToTable (data) {
  const dataRankArr = JSON.parse(JSON.stringify(data))
  dataRankArr.forEach((rank, i) => {
    const info = rank.submission_info
    Object.keys(info).forEach(problemID => {
      dataRankArr[i][problemID] = info[problemID]
    })
  })
  dataRank.value = dataRankArr
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

function downloadRankCSV () {
  utils.downloadFile(`contest_rank?download_csv=1&contest_id=${route.params.contestID}&force_refrash=${forceUpdate.value ? '1' : '0'}`)
}

onMounted(() => {
  contestID.value = route.params.contestID
  getData(1)
  if (contestProblems.value.length === 0) {
    getContestProblems(contestID.value)
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
