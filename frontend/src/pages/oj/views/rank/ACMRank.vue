<template>
  <el-row justify="space-around">
    <el-col :span="22">
      <Panel :padding="10">
        <template #title>문제 해결 순위</template>
        <template #extra>
          <!-- 공개 순위에서는 같은 학교 학생이 모두 "○○학교 학생"이라 구분되지 않는다.
               교사에게만 자기 학생끼리의 순위를 볼 수단을 준다. -->
          <el-switch v-if="userStore.isTeacher" v-model="myStudents" active-text="내 학생만"
                     @change="onFilterChange" />
        </template>
        <div class="echarts">
          <VChart ref="chart" :option="options" autoresize />
        </div>
      </Panel>
      <el-table :data="dataRank" v-loading="loadingTable" size="large" stripe
                :row-class-name="rowClassName">
        <el-table-column align="center" width="60">
          <template #default="{ $index }">{{ $index + (page - 1) * limit + 1 }}</template>
        </el-table-column>
        <el-table-column label="사용자" align="center">
          <template #default="{ row }">
            <!-- 수업용 학생은 표시 이름이 "○○학교 학생"이라 조회 키가 아니다. 링크를 걸지 않는다. -->
            <a v-if="row.user.profile_visible" class="link-text truncate"
               @click="router.push({ name: 'user-home', query: { username: row.user.username } })">
              {{ row.user.username }}
            </a>
            <span v-else class="truncate">{{ row.user.username }}</span>
          </template>
        </el-table-column>
        <el-table-column label="정답" align="center" prop="accepted_number" />
        <el-table-column label="총 제출" align="center" prop="submission_number" />
        <el-table-column label="레이팅" align="center">
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
import api from '@oj/api'
import Pagination from '@oj/components/Pagination.vue'
import utils from '@/utils/utils'
import { RULE_TYPE } from '@/utils/constants'
import { useUserStore } from '@/store/user'
const router = useRouter()
const userStore = useUserStore()
const myStudents = ref(false)

const page = ref(1)
const limit = ref(30)
const total = ref(0)
const loadingTable = ref(false)
const dataRank = ref([])
const chart = ref(null)

const options = ref({
  tooltip: { trigger: 'axis' },
  legend: { data: ['정답', '총 제출'] },
  grid: { x: '3%', x2: '3%' },
  toolbox: {
    show: true,
    feature: {
      dataView: { show: true, readOnly: true },
      magicType: { show: true, type: ['line', 'bar', 'stack'] },
      saveAsImage: { show: true }
    },
    right: '10%'
  },
  calculable: true,
  xAxis: [{
    type: 'category', data: ['root'],
    axisLabel: {
      interval: 0, showMinLabel: true, showMaxLabel: true, align: 'center',
      formatter: (value) => utils.breakLongWords(value, 10)
    }
  }],
  yAxis: [{ type: 'value' }],
  series: [
    { name: '정답', type: 'bar', data: [0], markPoint: { data: [{ type: 'max', name: 'max' }] } },
    { name: '총 제출', type: 'bar', data: [0], markPoint: { data: [{ type: 'max', name: 'max' }] } }
  ]
})

function getACRate (ac, total) {
  return utils.getACRate(ac, total)
}

function getRankData (p) {
  const offset = (p - 1) * limit.value
  loadingTable.value = true
  api.getUserRank(offset, limit.value, RULE_TYPE.ACM, myStudents.value).then(res => {
    loadingTable.value = false
    if (p === 1) changeCharts(res.data.data.results.slice(0, 10))
    total.value = res.data.data.total
    dataRank.value = res.data.data.results
  }).catch(() => {
    loadingTable.value = false
  })
}

function changeCharts (rankData) {
  const [usernames, acData, totalData] = [[], [], []]
  rankData.forEach(ele => {
    usernames.push(ele.user.username)
    acData.push(ele.accepted_number)
    totalData.push(ele.submission_number)
  })
  options.value.xAxis[0].data = usernames
  options.value.series[0].data = acData
  options.value.series[1].data = totalData
  options.value = { ...options.value }
}

// 같은 학교 학생이 여럿이면 이름만으로는 자기 줄을 못 찾는다
function rowClassName ({ row }) {
  return row.user.id === userStore.user.id ? 'my-row' : ''
}

function onFilterChange () {
  page.value = 1
  getRankData(1)
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
  :deep(.my-row) {
    background-color: #fdf6ec;
    font-weight: 600;
  }
</style>
