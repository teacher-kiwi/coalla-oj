<template>
  <div>
    <Panel shadow>
      <template #title>{{ contest.title || '대회' }}</template>
      <template #extra>
        <el-button @click="goList">목록</el-button>
        <el-button :icon="Edit" @click="openEdit">수정</el-button>
        <el-button type="primary" @click="goRank">순위 보기</el-button>
      </template>

      <el-descriptions :column="3" border size="small">
        <el-descriptions-item label="상태">
          <el-tag :type="STATUS_TAG[contest.status]" size="small">
            {{ STATUS_LABEL[contest.status] }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="시작">{{ localtime(contest.start_time) }}</el-descriptions-item>
        <el-descriptions-item label="종료">{{ localtime(contest.end_time) }}</el-descriptions-item>
      </el-descriptions>

      <el-alert v-if="!notStarted" type="info" show-icon :closable="false" class="locked">
        시작한 대회는 문제를 넣거나 뺄 수 없습니다. 배포 학급은 계속 바꿀 수 있습니다.
      </el-alert>
    </Panel>

    <Panel shadow class="section">
      <template #title>문제</template>
      <template #extra>
        <el-button type="primary" :icon="Plus" :disabled="!notStarted"
                   @click="openProblemDialog">문제 넣기</el-button>
      </template>

      <el-table v-loading="loading.problems" :data="problems" class="full-width">
        <el-table-column label="번호" prop="_id" width="80" />
        <el-table-column label="제목" prop="title" />
        <el-table-column label="난이도" width="120">
          <template #default="{ row }">{{ DIFFICULTY_LABEL[row.difficulty] || row.difficulty }}</template>
        </el-table-column>
        <el-table-column label="관리" width="100">
          <template #default="{ row }">
            <el-button size="small" type="danger" :disabled="!notStarted"
                       @click="removeProblem(row)">빼기</el-button>
          </template>
        </el-table-column>
      </el-table>
      <p v-if="!loading.problems && !problems.length" class="empty">
        아직 넣은 문제가 없습니다. 내가 만든 문제나 공개 문제를 넣을 수 있습니다.
      </p>
    </Panel>

    <Panel shadow class="section">
      <template #title>배포 학급</template>
      <template #extra>
        <el-button type="primary" :icon="Plus" @click="openClassDialog">학급에 배포</el-button>
      </template>

      <el-table v-loading="loading.classes" :data="assignments" class="full-width">
        <el-table-column label="학교" prop="school_name" />
        <el-table-column label="학급" prop="display_name" width="200" />
        <el-table-column label="학생 수" prop="student_count" width="100" />
        <el-table-column label="관리" width="100">
          <template #default="{ row }">
            <el-button size="small" type="danger" @click="removeClass(row)">배포 취소</el-button>
          </template>
        </el-table-column>
      </el-table>
      <p v-if="!loading.classes && !assignments.length" class="empty">
        배포한 학급이 없습니다. 배포해야 학생이 대회에 들어올 수 있습니다.
      </p>
    </Panel>

    <el-dialog v-model="editDialog" title="대회 수정" width="520px"
               :close-on-click-modal="false">
      <el-form label-width="80px">
        <el-form-item label="제목" required>
          <el-input v-model="form.title" maxlength="128" />
        </el-form-item>
        <el-form-item label="안내">
          <el-input v-model="form.description" type="textarea" :rows="3"
                    placeholder="학생에게 보이는 안내입니다" />
        </el-form-item>
        <el-form-item label="시작" required>
          <el-date-picker v-model="form.start_time" type="datetime" placeholder="시작 시각"
                          format="YYYY-MM-DD HH:mm" />
        </el-form-item>
        <el-form-item label="종료" required>
          <el-date-picker v-model="form.end_time" type="datetime" placeholder="종료 시각"
                          format="YYYY-MM-DD HH:mm" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialog = false">취소</el-button>
        <el-button type="primary" :loading="saving" @click="submitEdit">저장</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="problemDialog" title="문제 넣기" width="620px">
      <el-table :data="candidates" height="360" @row-click="addProblem" class="pick-table">
        <el-table-column label="번호" prop="_id" width="90" />
        <el-table-column label="제목" prop="title" />
        <el-table-column label="구분" width="100">
          <template #default="{ row }">{{ row.visibility === 'public' ? '공개' : '내 문제' }}</template>
        </el-table-column>
      </el-table>
      <p class="guide">줄을 누르면 대회에 들어갑니다. 원본은 그대로 남습니다.</p>
    </el-dialog>

    <el-dialog v-model="classDialog" title="학급에 배포" width="520px">
      <el-table :data="myClasses" @row-click="addClass" class="pick-table">
        <el-table-column label="학교" prop="school_name" />
        <el-table-column label="학급" prop="display_name" />
        <el-table-column label="학생 수" prop="student_count" width="100" />
      </el-table>
      <p class="guide">줄을 누르면 배포됩니다.</p>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Edit, Plus } from '@element-plus/icons-vue'
import api from '@oj/api'
import time from '@/utils/time'
import { CONTEST_STATUS, DIFFICULTY_LABEL } from '@/utils/constants'

const STATUS_LABEL = {
  [CONTEST_STATUS.NOT_START]: '시작 전',
  [CONTEST_STATUS.UNDERWAY]: '진행 중',
  [CONTEST_STATUS.ENDED]: '종료'
}
const STATUS_TAG = {
  [CONTEST_STATUS.NOT_START]: 'info',
  [CONTEST_STATUS.UNDERWAY]: 'success',
  [CONTEST_STATUS.ENDED]: ''
}

const route = useRoute()
const router = useRouter()
const contestId = parseInt(route.params.contestId)

const contest = ref({})
const problems = ref([])
const assignments = ref([])
const myClasses = ref([])
const candidates = ref([])
const problemDialog = ref(false)
const classDialog = ref(false)
const editDialog = ref(false)
const saving = ref(false)
const form = reactive({ title: '', description: '', start_time: '', end_time: '' })
const loading = reactive({ problems: false, classes: false })

const notStarted = computed(() => contest.value.status === CONTEST_STATUS.NOT_START)

function localtime (val) {
  return val ? time.utcToLocal(val, 'YYYY-M-D HH:mm') : ''
}

function goList () {
  router.push({ name: 'teacher-contest-list' })
}

function goRank () {
  router.push({ name: 'contest-rank', params: { contestID: contestId } })
}

function openEdit () {
  form.title = contest.value.title
  form.description = contest.value.description
  // 서버는 UTC 로 내려준다. 달력에는 Date 객체를 넣어야 그 지역 시각으로 보인다.
  form.start_time = new Date(contest.value.start_time)
  form.end_time = new Date(contest.value.end_time)
  editDialog.value = true
}

function submitEdit () {
  if (!form.title.trim()) {
    ElMessage.error('제목을 입력해주세요')
    return
  }
  if (!form.start_time || !form.end_time) {
    ElMessage.error('시작과 종료 시각을 정해주세요')
    return
  }
  saving.value = true
  api.editMyContest({
    id: contestId,
    title: form.title,
    description: form.description,
    // toISOString 은 타임존(Z)이 붙는다. 이걸 빼면 서버(TIME_ZONE=UTC)가
    // 교사가 고른 지역 시각을 그대로 UTC 로 읽어 그만큼 어긋난다.
    start_time: new Date(form.start_time).toISOString(),
    end_time: new Date(form.end_time).toISOString()
  }).then(() => {
    saving.value = false
    editDialog.value = false
    loadContest()
  }, () => {
    saving.value = false
  })
}

function loadContest () {
  api.getMyContest(contestId).then(res => { contest.value = res.data.data }, () => {})
}

function loadProblems () {
  loading.problems = true
  api.getMyContestProblems(contestId).then(res => {
    problems.value = res.data.data
    loading.problems = false
  }, () => {
    loading.problems = false
  })
}

function loadAssignments () {
  loading.classes = true
  api.getMyContestClasses(contestId).then(res => {
    assignments.value = res.data.data
    loading.classes = false
  }, () => {
    loading.classes = false
  })
}

function openProblemDialog () {
  // 내가 만든 문제와 공개 문제를 함께 고르게 한다
  Promise.all([
    api.getMyProblems(),
    api.getProblemList(0, 250, {})
  ]).then(([mine, publics]) => {
    const already = new Set(problems.value.map(p => p.title))
    const rows = [
      ...mine.data.data.map(p => ({ ...p, visibility: p.visibility })),
      ...publics.data.data.results.map(p => ({ ...p, visibility: 'public' }))
    ].filter(p => !already.has(p.title))
    candidates.value = rows
    problemDialog.value = true
  }).catch(() => {})
}

function addProblem (row) {
  api.addMyContestProblem(contestId, row.id).then(() => {
    problemDialog.value = false
    ElMessage.success('문제를 넣었습니다')
    loadProblems()
    loadContest()
  }, () => {})
}

function removeProblem (row) {
  api.removeMyContestProblem(contestId, row.id).then(() => {
    loadProblems()
    loadContest()
  }, () => {})
}

function openClassDialog () {
  api.getMyClasses().then(res => {
    const assigned = new Set(assignments.value.map(a => a.school_class))
    myClasses.value = res.data.data.filter(c => !assigned.has(c.id))
    classDialog.value = true
  }, () => {})
}

function addClass (row) {
  api.assignMyContest(contestId, row.id).then(() => {
    classDialog.value = false
    ElMessage.success('학급에 배포했습니다')
    loadAssignments()
    loadContest()
  }, () => {})
}

function removeClass (row) {
  api.unassignMyContest(contestId, row.school_class).then(() => {
    loadAssignments()
    loadContest()
  }, () => {})
}

onMounted(() => {
  loadContest()
  loadProblems()
  loadAssignments()
})
</script>

<style scoped>
.section {
  margin-top: 20px;
}

.locked {
  margin-top: 14px;
}

.guide {
  font-size: 13px;
  color: #909399;
  margin-top: 10px;
}

.empty {
  text-align: center;
  color: #909399;
  padding: 26px 0;
}

.pick-table :deep(tbody tr) {
  cursor: pointer;
}
</style>
