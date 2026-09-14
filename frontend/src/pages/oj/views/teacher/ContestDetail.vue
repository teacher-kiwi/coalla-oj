<template>
  <div>
    <!-- 이 판은 표가 아니라 대회 정보와 안내만 담는다. 아래 판들은 표라 여백이 없다. -->
    <Panel shadow :padding="20">
      <template #title>{{ contest.title || '대회' }}</template>
      <template #extra>
        <el-button @click="goList">목록</el-button>
        <el-button :icon="Edit" @click="openEdit">수정</el-button>
        <el-button type="primary" @click="goRank">순위 보기</el-button>
      </template>

      <Markdown v-if="contest.description" class="description" :source="contest.description" />

      <el-descriptions :column="3" border size="small">
        <el-descriptions-item label="상태">
          <el-tag :type="CONTEST_STATUS_REVERSE[contest.status]?.tag" size="small">
            {{ CONTEST_STATUS_REVERSE[contest.status]?.label }}
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
        <el-table-column label="번호" prop="display_id" width="80" />
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
        <template #empty>
          <span v-if="!loading.problems">아직 넣은 문제가 없습니다. 내가 만든 문제나 공개 문제를 넣을 수 있습니다.</span>
        </template>
      </el-table>
    </Panel>

    <Panel shadow class="section">
      <template #title>배포 학급</template>

      <!-- 내 학급을 모두 보여주고 스위치로 배포를 켜고 끈다.
           따로 고르는 대화상자를 열지 않아도 지금 어디에 나갔는지 한눈에 보인다. -->
      <el-table v-loading="loading.classes" :data="classRows" class="full-width">
        <el-table-column label="학교" prop="school_name" />
        <el-table-column label="학급" prop="display_name" />
        <el-table-column label="학생 수" prop="student_count" width="100" />
        <el-table-column label="배포" width="100">
          <template #default="{ row }">
            <el-switch :model-value="row.assigned" @change="toggleClass(row, $event)" />
          </template>
        </el-table-column>
        <template #empty>
          <span v-if="!loading.classes">만든 학급이 없습니다. "내 학급" 에서 학급을 만든 뒤 여기서 배포하세요.</span>
        </template>
      </el-table>
    </Panel>

    <Panel shadow class="section">
      <template #title>공지</template>
      <template #extra>
        <el-button type="primary" :icon="Plus" @click="openAnnouncement()">공지 쓰기</el-button>
      </template>

      <el-table v-loading="loading.announcements" :data="announcements" class="full-width">
        <el-table-column label="제목" prop="title" />
        <el-table-column label="작성 일시" width="180">
          <template #default="{ row }">{{ localtime(row.create_time) }}</template>
        </el-table-column>
        <el-table-column label="관리" width="160">
          <template #default="{ row }">
            <el-button size="small" @click="openAnnouncement(row)">수정</el-button>
            <el-button size="small" type="danger" @click="removeAnnouncement(row)">삭제</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <span v-if="!loading.announcements">공지가 없습니다. 대회 중에 알릴 것이 생기면 여기에 씁니다.</span>
        </template>
      </el-table>
      <p v-if="notStarted && announcements.length" class="guide panel-inset">
        공지는 대회가 시작한 뒤부터 학생에게 보입니다.
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

    <el-dialog v-model="problemDialog" title="문제 넣기" width="720px"
               :close-on-click-modal="false">
      <!-- 문제집의 문제 추가와 같은 방식이다(같은 기준으로 고르고 여러 개를 한 번에) -->
      <div class="picker-filter">
        <el-input v-model="keyword" placeholder="문제 제목이나 번호로 검색 (Enter)"
                  clearable @keyup.enter="searchProblems(1)" />
        <el-select v-model="difficulty" placeholder="난이도" clearable class="picker-difficulty"
                   @change="searchProblems(1)">
          <el-option v-for="d in DIFFICULTY" :key="d.value" :value="d.value" :label="d.label" />
        </el-select>
        <span class="picker-switch">
          <span class="picker-switch-label">즐겨찾기</span>
          <el-switch v-model="favoriteOnly" @change="searchProblems(1)" />
        </span>
      </div>
      <el-table v-loading="searching" :data="candidates"
                class="full-width candidate-table" @selection-change="onSelectionChange">
        <el-table-column type="selection" width="45" :selectable="canPick" />
        <el-table-column label="#" prop="display_id" width="100" />
        <el-table-column label="제목">
          <template #default="{ row }">
            {{ row.title }}
            <span v-if="!canPick(row)" class="already-in">넣어 둠</span>
          </template>
        </el-table-column>
        <el-table-column label="난이도" width="90">
          <template #default="{ row }"><DifficultyTag :value="row.difficulty" /></template>
        </el-table-column>
        <el-table-column label="범위" width="90" align="center">
          <template #default="{ row }"><ScopeTag :value="row.visibility" /></template>
        </el-table-column>
      </el-table>
      <p class="picker-guide">
        내가 만든 학급 문제도 넣을 수 있습니다. 배포한 학급 학생만 볼 수 있습니다.
      </p>
      <Pagination :total="candidateTotal" :page-size="10" :current="candidatePage"
                  @on-change="searchProblems" />
      <template #footer>
        <el-button @click="problemDialog = false">취소</el-button>
        <el-button type="primary" :loading="saving" @click="addProblems">
          {{ selected.length ? `${selected.length}개 넣기` : '넣기' }}
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="announcementDialog"
               :title="announcementForm.id ? '공지 수정' : '공지 쓰기'" width="560px"
               :close-on-click-modal="false">
      <el-form label-width="60px">
        <el-form-item label="제목" required>
          <el-input v-model="announcementForm.title" maxlength="128" />
        </el-form-item>
        <el-form-item label="내용" required>
          <el-input v-model="announcementForm.content" type="textarea" :rows="5"
                    placeholder="대회에 들어온 학생에게 보입니다" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="announcementDialog = false">취소</el-button>
        <el-button type="primary" :loading="saving" @click="submitAnnouncement">저장</el-button>
      </template>
    </el-dialog>

  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import Markdown from '@oj/components/Markdown.vue'
import ScopeTag from '@oj/components/ScopeTag.vue'
import DifficultyTag from '@oj/components/DifficultyTag.vue'
import Pagination from '@oj/components/Pagination.vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Edit, Plus } from '@element-plus/icons-vue'
import api from '@oj/api'
import time from '@/utils/time'
import { CONTEST_STATUS, CONTEST_STATUS_REVERSE, DIFFICULTY, DIFFICULTY_LABEL } from '@/utils/constants'

const route = useRoute()
const router = useRouter()
const contestId = parseInt(route.params.contestId)

const contest = ref({})
const problems = ref([])
// 이미 넣은 문제. 서버도 건너뛰지만, 고를 수 있으면 몇 개를 넣었는지 어긋나 보인다.
// (대회 문제 목록은 problem_id 를 id 로 준다)
const pickedIds = computed(() => new Set(problems.value.map(p => p.id)))

function canPick (row) {
  return !pickedIds.value.has(row.id)
}
const assignments = ref([])
const myClasses = ref([])
const candidates = ref([])
const candidateTotal = ref(0)
const candidatePage = ref(1)
const searching = ref(false)
const selected = ref([])
const keyword = ref('')
const difficulty = ref('')
const favoriteOnly = ref(false)
const announcements = ref([])
const problemDialog = ref(false)
const editDialog = ref(false)
const announcementDialog = ref(false)
const saving = ref(false)
const form = reactive({ title: '', description: '', start_time: '', end_time: '' })
const announcementForm = reactive({ id: null, title: '', content: '' })
const loading = reactive({ problems: false, classes: false, announcements: false })

const notStarted = computed(() => contest.value.status === CONTEST_STATUS.NOT_START)

// 내 학급 전부에 배포 여부를 붙인다
const classRows = computed(() => {
  const assigned = new Set(assignments.value.map(a => a.school_class))
  return myClasses.value.map(c => ({ ...c, assigned: assigned.has(c.id) }))
})

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
  // 내 학급 전부와 배포 현황을 함께 읽는다. 목록에는 둘을 합쳐 보여준다.
  Promise.all([api.getMyClasses(), api.getMyContestClasses(contestId)]).then(([classes, assigned]) => {
    myClasses.value = classes.data.data
    assignments.value = assigned.data.data
    loading.classes = false
  }).catch(() => {
    loading.classes = false
  })
}

function openProblemDialog () {
  keyword.value = ''
  difficulty.value = ''
  favoriteOnly.value = false
  selected.value = []
  problemDialog.value = true
  searchProblems(1)
}

function searchProblems (page) {
  candidatePage.value = page
  searching.value = true
  // 공개 문제와 내가 만든 학급 문제를 함께 고를 수 있어야 한다.
  // 빈 값은 getProblemList 가 알아서 뺀다.
  const params = {
    keyword: keyword.value,
    difficulty: difficulty.value,
    favorite: favoriteOnly.value ? '1' : '',
    mine: 1
  }
  api.getProblemList((page - 1) * 10, 10, params).then(res => {
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
    ElMessage.error('넣을 문제를 선택하세요')
    return
  }
  saving.value = true
  api.addMyContestProblems(contestId, selected.value.map(p => p.id)).then(res => {
    saving.value = false
    problemDialog.value = false
    ElMessage.success(`${res.data.data.added}개를 넣었습니다`)
    loadProblems()
    loadContest()
  }, () => {
    saving.value = false
  })
}

function removeProblem (row) {
  api.removeMyContestProblem(contestId, row.id).then(() => {
    loadProblems()
    loadContest()
  }, () => {})
}

function toggleClass (row, assign) {
  const request = assign
    ? api.assignMyContest(contestId, row.id)
    : api.unassignMyContest(contestId, row.id)
  request.then(() => {
    ElMessage.success(assign ? '학급에 배포했습니다' : '배포를 취소했습니다')
    loadAssignments()
    loadContest()
  }, () => {
    // 실패하면 스위치가 눌린 채로 남지 않도록 서버 상태를 다시 읽는다
    loadAssignments()
  })
}

function loadAnnouncements () {
  loading.announcements = true
  api.getMyContestAnnouncements(contestId).then(res => {
    announcements.value = res.data.data
    loading.announcements = false
  }, () => {
    loading.announcements = false
  })
}

// 인자가 없으면 새로 쓰기, 있으면 그 공지를 고친다
function openAnnouncement (row) {
  announcementForm.id = row ? row.id : null
  announcementForm.title = row ? row.title : ''
  announcementForm.content = row ? row.content : ''
  announcementDialog.value = true
}

function submitAnnouncement () {
  if (!announcementForm.title.trim() || !announcementForm.content.trim()) {
    ElMessage.error('제목과 내용을 입력해주세요')
    return
  }
  saving.value = true
  const request = announcementForm.id
    ? api.editMyContestAnnouncement(announcementForm.id, announcementForm.title,
      announcementForm.content)
    : api.createMyContestAnnouncement(contestId, announcementForm.title,
      announcementForm.content)
  request.then(() => {
    saving.value = false
    announcementDialog.value = false
    ElMessage.success(announcementForm.id ? '공지를 고쳤습니다' : '공지를 올렸습니다')
    loadAnnouncements()
  }, () => {
    saving.value = false
  })
}

function removeAnnouncement (row) {
  ElMessageBox.confirm('이 공지를 삭제하시겠습니까?', '공지 삭제', { type: 'warning' })
    .then(() => {
      api.deleteMyContestAnnouncement(row.id).then(() => loadAnnouncements(), () => {})
    }, () => {})
}

onMounted(() => {
  loadContest()
  loadProblems()
  loadAssignments()
  loadAnnouncements()
})
</script>

<style scoped>
.section {
  margin-top: 20px;
}

.locked {
  margin-top: 14px;
}

/* 교사가 대회를 만들 때 적은 안내. 학생도 같은 글을 본다.
   (teacher/ProblemSetDetail.vue 의 문제집 안내와 같은 모양이다) */
/* 교사가 적은 안내. 마크다운으로 그린다(학생 화면과 같은 렌더러).
   색·줄간격·줄바꿈은 마크다운 쪽이 정하므로 여기서는 간격만 잡는다. */
.description {
  margin-bottom: 12px;
}

.guide {
  font-size: 13px;
  color: #909399;
  margin-top: 10px;
}

/* 문제집의 문제 추가 대화상자와 같은 모양이다 */
.picker-filter {
  display: flex;
  align-items: center;
  gap: 10px;
}

.picker-difficulty {
  width: 130px;
  flex: none;
}

.picker-switch {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex: none;
}

.picker-switch-label {
  font-size: 13px;
  color: #606266;
  white-space: nowrap;
}

.already-in {
  margin-left: 6px;
  font-size: 12px;
  color: #909399;
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
</style>
