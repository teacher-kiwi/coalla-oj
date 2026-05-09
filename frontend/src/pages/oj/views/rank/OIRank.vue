<template>
  <el-row justify="space-around">
    <el-col :span="22">
      <Panel :padding="10">
        <template #title>{{ t('m.OI_Ranklist') }}</template>
        <div class="echarts">
          <VChart ref="chart" :option="options" autoresize />
        </div>
      </Panel>
      <el-table :data="dataRank" size="large" stripe>
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
        <el-table-column :label="t('m.mood')" align="center" prop="mood" />
        <el-table-column :label="t('m.Score')" align="center" prop="total_score" />
        <el-table-column :label="t('m.AC')" align="center" prop="accepted_number" />
        <el-table-column :label="t('m.Total')" align="center" prop="submission_number" />
        <el-table-column :label="t('m.Rating')" align="center">
          <template #default="{ row }">{{ getACRate(row.accepted_number, row.submission_number) }}</template>
        </el-table-column>
      </el-table>
      <Pagination :total="total" :page-size="limit" :current="page"
                  @on-change="onPageChange" :show-sizer="true"
                  @on-page-size-change="onPageSizeChange" />
    </el-col>
  </el-row>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import api from '@oj/api'
import Pagination from '@oj/components/Pagination.vue'
import utils from '@/utils/utils'
import { RULE_TYPE } from '@/utils/constants'

const { t } = useI18n()
const router = useRouter()

const page = ref(1)
const limit = ref(30)
const total = ref(0)
const dataRank = ref([])
const chart = ref(null)

const options = ref({
  tooltip: { trigger: 'axis' },
  legend: { data: [t('m.Score')] },
  grid: { x: '3%', x2: '3%' },
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
    name: t('m.Score'), type: 'bar', data: [0], barMaxWidth: '80',
    markPoint: { data: [{ type: 'max', name: 'max' }] }
  }]
})

function getACRate (ac, total) {
  return utils.getACRate(ac, total)
}

function getRankData (p) {
  const offset = (p - 1) * limit.value
  api.getUserRank(offset, limit.value, RULE_TYPE.OI).then(res => {
    if (p === 1) changeCharts(res.data.data.results.slice(0, 10))
    total.value = res.data.data.total
    dataRank.value = res.data.data.results
  })
}

function changeCharts (rankData) {
  const [usernames, scores] = [[], []]
  rankData.forEach(ele => {
    usernames.push(ele.user.username)
    scores.push(ele.total_score)
  })
  options.value.xAxis[0].data = usernames
  options.value.series[0].data = scores
  options.value = { ...options.value }
}

function onPageChange (newPage) {
  page.value = newPage
  getRankData(newPage)
}

function onPageSizeChange (newSize) {
  limit.value = newSize
  page.value = 1
  getRankData(1)
}

onMounted(() => {
  getRankData(1)
})
</script>

<style scoped lang="less">
  .echarts {
    margin: 0 auto;
    width: 95%;
    height: 400px;
  }
  .link-text {
    color: #57a3f3;
    cursor: pointer;
  }
  .truncate {
    display: inline-block;
    max-width: 200px;
  }
</style>
