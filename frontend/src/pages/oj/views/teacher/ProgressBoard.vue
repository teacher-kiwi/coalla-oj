<template>
  <Panel shadow>
    <template #title>학습 현황</template>
    <template #extra>
      <el-button :disabled="!canQuery" @click="download">엑셀로 내려받기</el-button>
    </template>

    <div class="selectors">
      <el-select v-model="classId" placeholder="학급 선택" class="selector" @change="load">
        <el-option v-for="item in classes" :key="item.id" :value="item.id"
                   :label="`${item.school_name} ${item.grade}학년 ${item.class_no}반`" />
      </el-select>
      <el-select v-model="problemSetId" placeholder="문제집 선택" class="selector" @change="load">
        <el-option v-for="item in problemSets" :key="item.id" :value="item.id" :label="item.title" />
      </el-select>
    </div>

    <div v-if="board" class="legend">
      <span><b>O</b> 해결</span>
      <span><b>△</b> 시도했지만 아직 못 풂 (괄호는 제출 횟수)</span>
      <span>빈칸 손대지 않음</span>
    </div>

    <el-table v-if="board" v-loading="loading" :data="board.students" class="full-width" size="small">
      <el-table-column label="번호" width="70" fixed>
        <template #default="{ row }">
          <el-button link type="primary" @click="goStudent(row)">{{ row.number }}</el-button>
        </template>
      </el-table-column>
      <el-table-column v-for="(problem, index) in board.problems" :key="problem.id"
                       :label="problem._id" align="center" width="80">
        <template #header>
          <el-tooltip :content="problem.title" placement="top">
            <span>{{ problem._id }}</span>
          </el-tooltip>
        </template>
        <template #default="{ row }">
          <span :class="cellClass(row.cells[index])">{{ cellText(row.cells[index]) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="해결" align="center" width="90" fixed="right">
        <template #default="{ row }">{{ row.solved_count }} / {{ board.problems.length }}</template>
      </el-table-column>
    </el-table>

    <p v-if="board && !board.students.length" class="empty">이 학급에 학생 계정이 없습니다.</p>

    <div v-if="board && board.students.length" class="totals">
      <span v-for="(total, index) in board.totals" :key="index" class="total-item">
        <b>{{ board.problems[index]._id }}</b>
        해결 {{ total.solved }}명 · 시도 {{ total.tried }}명
      </span>
    </div>

    <p v-if="!board && !loading" class="empty">학급과 문제집을 고르면 진도표가 나옵니다.</p>
  </Panel>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@oj/api'

const router = useRouter()
const loading = ref(false)
const classes = ref([])
const problemSets = ref([])
const classId = ref(null)
const problemSetId = ref(null)
const board = ref(null)

const canQuery = computed(() => !!classId.value && !!problemSetId.value)

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
  if (!canQuery.value) return
  loading.value = true
  api.getProblemSetProgress(problemSetId.value, classId.value).then(res => {
    loading.value = false
    board.value = res.data.data
  }, () => {
    loading.value = false
  })
}

function download () {
  window.open('/api/teacher/problem_set/progress?download=1' +
    `&problem_set=${problemSetId.value}&class_id=${classId.value}`)
}

function goStudent (row) {
  router.push({ name: 'teacher-student-detail', params: { membershipId: row.membership },
                query: { number: row.number } })
}

onMounted(() => {
  api.getMyClasses().then(res => { classes.value = res.data.data }, () => {})
  api.getMyProblemSets().then(res => { problemSets.value = res.data.data }, () => {})
})
</script>

<style scoped>
.full-width {
  width: 100%;
}

.selectors {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.selector {
  width: 260px;
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

.totals {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin-top: 14px;
  font-size: 12px;
  color: #606266;
}

.total-item {
  white-space: nowrap;
}

.empty {
  text-align: center;
  color: #909399;
  padding: 30px 0;
}
</style>
