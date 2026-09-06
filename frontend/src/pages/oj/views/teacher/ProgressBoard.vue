<template>
  <Panel shadow>
    <template #title>{{ title }}</template>
    <template #extra>
      <el-button @click="goSet">문제집</el-button>
      <el-button :disabled="!board" @click="download">엑셀로 내려받기</el-button>
    </template>

    <div v-if="board" class="legend panel-inset">
      <span><b>O</b> 해결</span>
      <span><b>△</b> 시도했지만 아직 못 풂 (괄호는 제출 횟수)</span>
      <span>빈칸 손대지 않음</span>
    </div>

    <el-table v-if="board" v-loading="loading" :data="board.students" class="full-width" size="small"
              :show-summary="!!board.students.length" :summary-method="summary">
      <el-table-column label="번호" width="70" fixed>
        <template #default="{ row }">{{ row.number }}</template>
      </el-table-column>
      <el-table-column label="이름" width="130" fixed>
        <template #default="{ row }">
          <el-button link type="primary" @click="goStudent(row)">{{ row.nickname }}</el-button>
        </template>
      </el-table-column>
      <el-table-column v-for="(problem, index) in board.problems" :key="problem.id"
                       :label="problem.display_id" align="center" width="80">
        <template #header>
          <el-tooltip :content="problem.title" placement="top">
            <span>{{ problem.display_id }}</span>
          </el-tooltip>
        </template>
        <template #default="{ row }">
          <span :class="cellClass(row.cells[index])">{{ cellText(row.cells[index]) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="해결" align="center" width="90" fixed="right">
        <template #default="{ row }">{{ row.solved_count }} / {{ board.problems.length }}</template>
      </el-table-column>
      <template #empty>
        <span v-if="!loading">이 학급에 학생 계정이 없습니다.</span>
      </template>
    </el-table>
  </Panel>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@oj/api'

const route = useRoute()
const router = useRouter()
// 어느 문제집을 어느 학급이 얼마나 풀었는지. 둘 다 주소로 정해져 온다.
const setId = parseInt(route.params.setId)
const classId = parseInt(route.params.classId)

const loading = ref(false)
const board = ref(null)

// 응답이 문제집 제목과 학급 이름을 함께 준다. 따로 부르지 않는다.
const title = computed(() => board.value
  ? `${board.value.problem_set.title} · ${board.value.school_class.name}`
  : '학습 현황')

// 반 전체 집계는 표 아래 따로 두지 않고 마지막 행으로 넣는다.
// 열 순서는 번호, 이름, 문제들..., 해결 이라 문제는 2 번째부터다.
// (범위 밖 인덱스는 undefined 라 번호·해결 칸은 저절로 빈칸이 된다)
function summary ({ columns }) {
  return columns.map((column, index) => {
    if (index === 1) return '해결/시도'
    const total = board.value.totals[index - 2]
    return total ? `${total.solved}/${total.tried}` : ''
  })
}

function cellText (cell) {
  if (cell.solved) return 'O'
  if (cell.attempts) return `△(${cell.attempts})`
  return ''
}

function cellClass (cell) {
  if (cell.solved) return 'solved'
  return cell.attempts ? 'tried' : ''
}

function load () {
  loading.value = true
  api.getProblemSetProgress(setId, classId).then(res => {
    loading.value = false
    board.value = res.data.data
  }, () => {
    loading.value = false
  })
}

function download () {
  window.open('/api/teacher/problem_set/progress?download=1' +
    `&problem_set=${setId}&class_id=${classId}`)
}

function goSet () {
  router.push({ name: 'teacher-problem-set-detail', params: { setId } })
}

function goStudent (row) {
  router.push({ name: 'teacher-student-detail', params: { membershipId: row.membership },
                query: { number: row.number, nickname: row.nickname } })
}

onMounted(load)
</script>

<style scoped>
.full-width {
  width: 100%;
}

.legend {
  display: flex;
  gap: 18px;
  font-size: 12px;
  color: #909399;
  margin-bottom: 10px;
}

.solved {
  color: #19be6b;
  font-weight: 600;
}

.tried {
  color: #e6a23c;
}

</style>
