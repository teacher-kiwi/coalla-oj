<template>
  <div>
    <Panel shadow>
      <template #title>{{ info.title || '문제집' }}</template>
      <template #extra>
        <el-button @click="goList">목록</el-button>
        <el-button @click="openEditDialog">수정</el-button>
        <el-button type="primary" :icon="Plus" @click="openProblemDialog">문제 추가</el-button>
      </template>

      <Markdown v-if="info.description" class="description panel-inset" :source="info.description" />

      <el-table v-loading="loading" :data="info.items" class="full-width">
        <el-table-column label="순서" width="70">
          <template #default="{ $index }">{{ $index + 1 }}</template>
        </el-table-column>
        <el-table-column label="#" width="100">
          <template #default="{ row }">{{ row.problem.display_id }}</template>
        </el-table-column>
        <el-table-column label="제목">
          <template #default="{ row }">
            <el-button link type="primary" @click="goProblem(row.problem.display_id)">
              {{ row.problem.title }}
            </el-button>
          </template>
        </el-table-column>
        <el-table-column label="난이도" width="100">
          <template #default="{ row }"><DifficultyTag :value="row.problem.difficulty" /></template>
        </el-table-column>
        <el-table-column label="범위" width="150" align="center">
          <template #default="{ row }">
            <!-- 담아둔 뒤에 관리자가 감춘 문제를 교사가 알아야 한다.
                 감춘 것은 학급/공개와 다른 축이라 이때만 따로 표시한다. -->
            <el-tooltip v-if="!row.problem_visible"
                        content="관리자가 감춘 문제입니다. 학생은 풀 수 없습니다." placement="top">
              <el-tag size="small" type="danger" effect="plain">풀 수 없음</el-tag>
            </el-tooltip>
            <el-tooltip v-else-if="row.problem_visibility === 'private'"
                        content="학급 문제입니다. 이 문제집을 배포한 학급만 볼 수 있습니다."
                        placement="top">
              <ScopeTag value="private" />
            </el-tooltip>
            <ScopeTag v-else :value="row.problem_visibility" />
          </template>
        </el-table-column>
        <el-table-column label="관리" width="240">
          <template #default="{ row, $index }">
            <el-button size="small" :disabled="$index === 0" @click="move($index, -1)">위로</el-button>
            <el-button size="small" :disabled="$index === info.items.length - 1"
                       @click="move($index, 1)">아래로</el-button>
            <el-button size="small" type="danger" @click="removeItem(row)">빼기</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <span v-if="!loading">담긴 문제가 없습니다. "문제 추가"로 문제를 골라 담으세요.</span>
        </template>
      </el-table>

      <p v-if="hasBlocked" class="notice panel-inset">
        <b>풀 수 없음</b> 으로 표시된 문제는 관리자가 감춘 것입니다. 학생 화면에도
        "지금 풀 수 없습니다" 로 나옵니다. 문제집에서 빼거나, 내가 만든 문제라면
        고쳐서 다시 공개를 신청하세요.
      </p>
    </Panel>

    <Panel shadow class="assignment-panel">
      <template #title>배포 학급</template>

      <!-- 내 학급을 모두 보여주고 스위치로 배포를 켜고 끈다. 배포한 학급의
           학생에게만 보인다. (대회 상세의 배포 학급 표와 같은 모양이다) -->
      <el-table :data="classRows" class="full-width">
        <el-table-column label="학교" prop="school_name" />
        <el-table-column label="학급" width="200">
          <template #default="{ row }">
            <!-- 학급을 누르면 이 문제집의 학습 현황으로 간다.
                 배포를 내린 학급도 그동안의 기록이 남아 있어 막지 않는다. -->
            <el-button link type="primary" @click="goProgress(row)">{{ row.display_name }}</el-button>
          </template>
        </el-table-column>
        <el-table-column label="학생 수" prop="student_count" width="100" />
        <el-table-column label="배포" width="100">
          <template #default="{ row }">
            <el-switch :model-value="!!row.assignment" @change="toggleAssign(row, $event)" />
          </template>
        </el-table-column>
        <template #empty>
          <span v-if="!loading">만든 학급이 없습니다. "내 학급" 에서 학급을 만든 뒤 여기서 배포하세요.</span>
        </template>
      </el-table>
      <p class="field-help panel-inset">
        학급 이름을 누르면 그 학급의 학습 현황을 볼 수 있습니다.
        배포를 끄면 학생 화면에서 사라집니다.
      </p>
    </Panel>

    <el-dialog v-model="editDialogVisible" title="문제집 수정" width="460px"
               :close-on-click-modal="false">
      <el-form label-width="80px">
        <el-form-item label="제목" required>
          <el-input v-model="editForm.title" maxlength="128" placeholder="예: 3주차 반복문" />
        </el-form-item>
        <el-form-item label="설명">
          <el-input v-model="editForm.description" type="textarea" :rows="3" maxlength="1024"
                    placeholder="학생에게 보이는 안내입니다" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">취소</el-button>
        <el-button type="primary" :loading="saving" @click="submitEdit">저장</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="problemDialogVisible" title="문제 추가" width="720px"
               :close-on-click-modal="false">
      <el-input v-model="keyword" placeholder="문제 제목이나 번호로 검색 (Enter)"
                clearable @keyup.enter="searchProblems(1)" />
      <el-table v-loading="searching" :data="candidates"
                class="full-width candidate-table" @selection-change="onSelectionChange">
        <el-table-column type="selection" width="45" />
        <el-table-column label="#" prop="display_id" width="100" />
        <el-table-column label="제목" prop="title" />
        <el-table-column label="난이도" width="90">
          <template #default="{ row }"><DifficultyTag :value="row.difficulty" /></template>
        </el-table-column>
        <el-table-column label="범위" width="90" align="center">
          <template #default="{ row }"><ScopeTag :value="row.visibility" /></template>
        </el-table-column>
      </el-table>
      <p class="picker-guide">
        내가 만든 학급 문제도 담을 수 있습니다. 배포한 학급 학생만 볼 수 있습니다.
      </p>
      <Pagination :total="candidateTotal" :page-size="10" :current="candidatePage"
                  @on-change="searchProblems" />
      <template #footer>
        <el-button @click="problemDialogVisible = false">취소</el-button>
        <el-button type="primary" :loading="saving" @click="addProblems">
          {{ selected.length ? `${selected.length}개 추가` : '추가' }}
        </el-button>
      </template>
    </el-dialog>

  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import Markdown from '@oj/components/Markdown.vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '@oj/api'
import DifficultyTag from '@oj/components/DifficultyTag.vue'
import ScopeTag from '@oj/components/ScopeTag.vue'
import Pagination from '@oj/components/Pagination.vue'

const route = useRoute()
const router = useRouter()
const setId = parseInt(route.params.setId)

const loading = ref(false)
const saving = ref(false)
const info = ref({ items: [], assignments: [] })
const hasBlocked = computed(() => info.value.items.some(i => !i.problem_visible))

const editDialogVisible = ref(false)
const editForm = reactive({ title: '', description: '' })

const problemDialogVisible = ref(false)
const searching = ref(false)
const keyword = ref('')
const candidates = ref([])
const candidateTotal = ref(0)
const candidatePage = ref(1)
const selected = ref([])

const myClasses = ref([])


// 목록 화면의 "수정" 과 같은 칸을 쓴다(제목과 설명).
function openEditDialog () {
  editForm.title = info.value.title || ''
  editForm.description = info.value.description || ''
  editDialogVisible.value = true
}

function submitEdit () {
  if (!editForm.title.trim()) {
    ElMessage.error('제목을 입력하세요')
    return
  }
  saving.value = true
  api.editProblemSet({
    id: setId,
    title: editForm.title.trim(),
    description: editForm.description
  }).then(() => {
    saving.value = false
    editDialogVisible.value = false
    load()
  }, () => {
    saving.value = false
  })
}

// 내 학급 전부에 배포 정보를 붙인다
const classRows = computed(() => {
  const byClass = new Map(info.value.assignments.map(a => [a.school_class, a]))
  return myClasses.value.map(c => ({ ...c, assignment: byClass.get(c.id) || null }))
})

function loadMyClasses () {
  api.getMyClasses().then(res => { myClasses.value = res.data.data }, () => {})
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

function goProgress (row) {
  router.push({ name: 'teacher-problem-set-progress',
                params: { setId, classId: row.id } })
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
  // 공개 문제와 내가 만든 학급 문제를 함께 고를 수 있어야 한다
  api.getProblemList((page - 1) * 10, 10, { keyword: keyword.value, mine: 1 }).then(res => {
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

function toggleAssign (row, assign) {
  const request = assign
    ? api.assignProblemSet({ problem_set: setId, school_class: row.id })
    : api.deleteProblemSetAssignment(row.assignment.id)
  request.then(() => {
    ElMessage.success(assign ? '배포했습니다' : '배포를 취소했습니다')
    load()
  }, load)   // 실패하면 스위치가 눌린 채 남지 않도록 서버 상태를 다시 읽는다
}


onMounted(() => {
  load()
  loadMyClasses()
})
</script>

<style scoped>
.full-width {
  width: 100%;
}

.assignment-panel {
  margin-top: 20px;
}

.notice {
  margin-top: 12px;
  font-size: 12px;
  color: #909399;
  line-height: 1.7;
}

/* 교사가 적은 안내. 마크다운으로 그린다(학생 화면과 같은 렌더러).
   색·줄간격·줄바꿈은 마크다운 쪽이 정하므로 여기서는 간격만 잡는다. */
.description {
  margin-bottom: 12px;
}

.picker-guide {
  font-size: 12px;
  color: #909399;
  line-height: 1.6;
  margin-top: 8px;
}

.candidate-table {
  margin-top: 12px;
}

.field-help {
  font-size: 12px;
  color: #909399;
  line-height: 1.6;
}

</style>
