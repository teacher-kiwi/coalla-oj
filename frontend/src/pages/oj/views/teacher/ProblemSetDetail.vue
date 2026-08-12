<template>
  <div>
    <Panel shadow>
      <template #title>{{ info.title || '문제집' }}</template>
      <template #extra>
        <el-button @click="goList">목록</el-button>
        <el-button type="primary" :icon="Plus" @click="openProblemDialog">문제 추가</el-button>
      </template>

      <p v-if="info.description" class="description">{{ info.description }}</p>

      <el-table v-loading="loading" :data="info.items" class="full-width">
        <el-table-column label="순서" width="70">
          <template #default="{ $index }">{{ $index + 1 }}</template>
        </el-table-column>
        <el-table-column label="#" width="100">
          <template #default="{ row }">{{ row.problem._id }}</template>
        </el-table-column>
        <el-table-column label="제목">
          <template #default="{ row }">
            <el-button link type="primary" @click="goProblem(row.problem._id)">
              {{ row.problem.title }}
            </el-button>
          </template>
        </el-table-column>
        <el-table-column label="난이도" width="100">
          <template #default="{ row }">{{ DIFFICULTY_LABEL[row.problem.difficulty] }}</template>
        </el-table-column>
        <el-table-column label="관리" width="240">
          <template #default="{ row, $index }">
            <el-button size="small" :disabled="$index === 0" @click="move($index, -1)">위로</el-button>
            <el-button size="small" :disabled="$index === info.items.length - 1"
                       @click="move($index, 1)">아래로</el-button>
            <el-button size="small" type="danger" @click="removeItem(row)">빼기</el-button>
          </template>
        </el-table-column>
      </el-table>

      <p v-if="!loading && !info.items.length" class="empty">
        담긴 문제가 없습니다. "문제 추가"로 공개 문제를 골라 담으세요.
      </p>
    </Panel>

    <Panel shadow class="assignment-panel">
      <template #title>배포한 학급</template>
      <template #extra>
        <el-button type="primary" :icon="Plus" @click="openAssignDialog">학급에 배포</el-button>
      </template>

      <el-table :data="info.assignments" class="full-width">
        <el-table-column label="학급" prop="class_name" />
        <el-table-column label="마감일" width="200">
          <template #default="{ row }">
            {{ row.due_at ? localtime(row.due_at) : '없음' }}
          </template>
        </el-table-column>
        <el-table-column label="공개" width="100">
          <template #default="{ row }">
            <el-switch :model-value="row.is_open" @change="toggleOpen(row, $event)" />
          </template>
        </el-table-column>
        <el-table-column label="관리" width="120">
          <template #default="{ row }">
            <el-button size="small" type="danger" @click="removeAssignment(row)">배포 취소</el-button>
          </template>
        </el-table-column>
      </el-table>

      <p v-if="!loading && !info.assignments.length" class="empty">
        아직 배포한 학급이 없습니다. 배포해야 학생 화면에 나타납니다.
      </p>
    </Panel>

    <el-dialog v-model="problemDialogVisible" title="문제 추가" width="720px"
               :close-on-click-modal="false">
      <el-input v-model="keyword" placeholder="문제 제목이나 번호로 검색 (Enter)"
                clearable @keyup.enter="searchProblems(1)" />
      <el-table v-loading="searching" :data="candidates"
                class="full-width candidate-table" @selection-change="onSelectionChange">
        <el-table-column type="selection" width="45" />
        <el-table-column label="#" prop="_id" width="100" />
        <el-table-column label="제목" prop="title" />
        <el-table-column label="난이도" width="90">
          <template #default="{ row }">{{ DIFFICULTY_LABEL[row.difficulty] }}</template>
        </el-table-column>
      </el-table>
      <Pagination :total="candidateTotal" :page-size="10" :current="candidatePage"
                  @on-change="searchProblems" />
      <template #footer>
        <el-button @click="problemDialogVisible = false">취소</el-button>
        <el-button type="primary" :loading="saving" @click="addProblems">
          {{ selected.length ? `${selected.length}개 추가` : '추가' }}
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="assignDialogVisible" title="학급에 배포" width="460px"
               :close-on-click-modal="false">
      <el-form label-width="90px">
        <el-form-item label="학급" required>
          <el-select v-model="assignForm.school_class" placeholder="학급을 선택하세요" class="full-width">
            <el-option v-for="item in myClasses" :key="item.id" :value="item.id"
                       :label="`${item.school_name} ${item.grade}학년 ${item.class_no}반`" />
          </el-select>
        </el-form-item>
        <el-form-item label="마감일">
          <el-date-picker v-model="assignForm.due_at" type="datetime" placeholder="정하지 않음"
                          class="full-width" />
        </el-form-item>
      </el-form>
      <p class="field-help">
        마감일은 안내용입니다. 지나도 문제는 계속 풀 수 있습니다.
      </p>
      <template #footer>
        <el-button @click="assignDialogVisible = false">취소</el-button>
        <el-button type="primary" :loading="saving" @click="assign">배포</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '@oj/api'
import time from '@/utils/time'
import { DIFFICULTY_LABEL } from '@/utils/constants'
import Pagination from '@oj/components/Pagination.vue'

const route = useRoute()
const router = useRouter()
const setId = parseInt(route.params.setId)

const loading = ref(false)
const saving = ref(false)
const info = ref({ items: [], assignments: [] })

const problemDialogVisible = ref(false)
const searching = ref(false)
const keyword = ref('')
const candidates = ref([])
const candidateTotal = ref(0)
const candidatePage = ref(1)
const selected = ref([])

const assignDialogVisible = ref(false)
const myClasses = ref([])
const assignForm = reactive({ school_class: null, due_at: null })

function localtime (val) {
  return time.utcToLocal(val)
}

function load () {
  loading.value = true
  api.getProblemSetForTeacher(setId).then(res => {
    loading.value = false
    info.value = res.data.data
  }, () => {
    loading.value = false
  })
}

function goList () {
  router.push({ name: 'teacher-problem-set-list' })
}

function goProblem (problemID) {
  router.push({ name: 'problem-details', params: { problemID } })
}

// ---- 문제 ----

function openProblemDialog () {
  keyword.value = ''
  selected.value = []
  problemDialogVisible.value = true
  searchProblems(1)
}

function searchProblems (page) {
  candidatePage.value = page
  searching.value = true
  api.getProblemList((page - 1) * 10, 10, { keyword: keyword.value }).then(res => {
    searching.value = false
    candidates.value = res.data.data.results
    candidateTotal.value = res.data.data.total
  }, () => {
    searching.value = false
  })
}

function onSelectionChange (rows) {
  selected.value = rows
}

function addProblems () {
  if (!selected.value.length) {
    ElMessage.error('추가할 문제를 선택하세요')
    return
  }
  saving.value = true
  api.addProblemSetProblems(setId, selected.value.map(p => p.id)).then(res => {
    saving.value = false
    problemDialogVisible.value = false
    ElMessage.success(`${res.data.data.added}개를 담았습니다`)
    load()
  }, () => {
    saving.value = false
  })
}

function move (index, delta) {
  const items = info.value.items.slice()
  const target = index + delta
  ;[items[index], items[target]] = [items[target], items[index]]
  // 서버가 순서를 확정하므로 화면은 응답을 받은 뒤 다시 그린다
  api.reorderProblemSetItems(setId, items.map(i => i.id)).then(load).catch(() => {})
}

function removeItem (row) {
  ElMessageBox.confirm(`"${row.problem.title}" 문제를 문제집에서 뺍니다.`, '문제 빼기', {
    confirmButtonText: '빼기', cancelButtonText: '취소'
  }).then(() => {
    api.deleteProblemSetItem(row.id).then(load).catch(() => {})
  }).catch(() => {})
}

// ---- 배포 ----

function openAssignDialog () {
  assignForm.school_class = null
  assignForm.due_at = null
  assignDialogVisible.value = true
  api.getMyClasses().then(res => {
    myClasses.value = res.data.data
  }, () => {})
}

function assign () {
  if (!assignForm.school_class) {
    ElMessage.error('학급을 선택하세요')
    return
  }
  saving.value = true
  api.assignProblemSet({
    problem_set: setId,
    school_class: assignForm.school_class,
    due_at: assignForm.due_at || null
  }).then(() => {
    saving.value = false
    assignDialogVisible.value = false
    ElMessage.success('배포했습니다')
    load()
  }, () => {
    saving.value = false
  })
}

function toggleOpen (row, value) {
  api.editProblemSetAssignment({ id: row.id, is_open: value }).then(load).catch(load)
}

function removeAssignment (row) {
  ElMessageBox.confirm(
    `${row.class_name}에서 이 문제집을 내립니다. 학생 화면에서 사라집니다.`,
    '배포 취소', { confirmButtonText: '취소하기', cancelButtonText: '닫기', type: 'warning' }
  ).then(() => {
    api.deleteProblemSetAssignment(row.id).then(load).catch(() => {})
  }).catch(() => {})
}

onMounted(load)
</script>

<style scoped>
.full-width {
  width: 100%;
}

.assignment-panel {
  margin-top: 20px;
}

.description {
  color: #606266;
  line-height: 1.7;
  margin-bottom: 12px;
  white-space: pre-wrap;
}

.candidate-table {
  margin-top: 12px;
}

.field-help {
  font-size: 12px;
  color: #909399;
  line-height: 1.6;
}

.empty {
  text-align: center;
  color: #909399;
  padding: 30px 0;
}
</style>
