<template>
  <Panel shadow>
    <template #title>{{ number !== null ? `${number}번 학생 제출 기록` : '학생 제출 기록' }}</template>
    <template #extra>
      <el-button @click="router.back()">뒤로</el-button>
    </template>

    <el-table v-loading="loading" :data="submissions" class="full-width">
      <el-table-column label="시간" width="180">
        <template #default="{ row }">{{ localtime(row.create_time) }}</template>
      </el-table-column>
      <el-table-column label="문제" width="120" prop="problem" />
      <el-table-column label="제목" prop="problem_title" />
      <el-table-column label="결과" width="140" align="center">
        <template #default="{ row }">
          <el-tag :type="JUDGE_STATUS[row.result].type">{{ JUDGE_STATUS[row.result].label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="언어" width="110" prop="language" />
      <el-table-column label="코드" width="90" align="center">
        <template #default="{ row }">
          <!-- 코드 열람은 제출 상세 화면을 그대로 쓴다. 담당 교사는 권한 검사를 통과한다. -->
          <el-button link type="primary" @click="router.push('/status/' + row.id)">보기</el-button>
        </template>
      </el-table-column>
    </el-table>

    <p v-if="!loading && !submissions.length" class="empty">아직 제출한 기록이 없습니다.</p>

    <Pagination :total="total" :page-size="limit" :current="page" @on-change="onPageChange" />
  </Panel>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@oj/api'
import time from '@/utils/time'
import { JUDGE_STATUS } from '@/utils/constants'
import Pagination from '@oj/components/Pagination.vue'

const route = useRoute()
const router = useRouter()
const membershipId = route.params.membershipId

const loading = ref(false)
const submissions = ref([])
const total = ref(0)
const page = ref(1)
const limit = 15
// 진도표에서 넘어오면 번호를 함께 받아 제목에 쓴다(한 번 더 조회하지 않기 위해)
const number = ref(route.query.number ? parseInt(route.query.number) : null)

function localtime (val) {
  return time.utcToLocal(val)
}

function load () {
  loading.value = true
  api.getStudentSubmissions(membershipId, (page.value - 1) * limit, limit,
                            route.query.problem_id).then(res => {
    loading.value = false
    submissions.value = res.data.data.results
    total.value = res.data.data.total
  }, () => {
    loading.value = false
  })
}

function onPageChange (newPage) {
  page.value = newPage
  load()
}

onMounted(load)
</script>

<style scoped>
.full-width {
  width: 100%;
}

.empty {
  text-align: center;
  color: #909399;
  padding: 30px 0;
}
</style>
