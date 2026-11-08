<template>
  <div>
    <Panel shadow>
      <template #title>
        <span class="title">{{ homework.title || '바로 과제' }}</span>
        <el-tag v-if="homework.ended" type="info" effect="plain" class="state">종료</el-tag>
        <el-tag v-else-if="homework.id" type="success" class="state">진행 중</el-tag>
      </template>
      <template #extra>
        <el-button @click="router.push({ name: 'teacher-homework-report' })">레포트</el-button>
        <el-button @click="editTitle">제목 수정</el-button>
        <el-button :disabled="!homework.id" @click="download">엑셀로 내려받기</el-button>
        <el-button v-if="homework.ended" type="danger" plain @click="remove">과제 삭제</el-button>
      </template>

      <div v-if="homework.id" class="summary">
        <div class="code-box" @click="showCode = true">
          <span class="code-label">입장 코드</span>
          <span class="code">{{ homework.code }}</span>
          <span class="code-hint">눌러서 크게 보기</span>
        </div>
        <div class="facts">
          <p>
            <span class="label">주소</span>
            <a :href="link" target="_blank" rel="noopener">{{ link }}</a>
            <el-button size="small" link type="primary" @click="copyLink">복사</el-button>
          </p>
          <p>
            <span class="label">{{ homework.ended ? '종료' : '마감' }}</span>
            {{ localtime(homework.ended_at || homework.end_time) }}
            <span v-if="!homework.ended" class="muted">({{ remaining }})</span>
            <el-button v-if="!homework.ended" size="small" link type="primary" @click="openDeadline">
              바꾸기
            </el-button>
          </p>
          <p>
            <span class="label">언어</span>
            {{ homework.languages.map(l => l === 'Block Coding' ? '블록 코딩' : l).join(', ') }}
          </p>
          <p v-if="!homework.ended" class="controls">
            <span class="label">새 입장</span>
            <el-switch :model-value="!homework.entry_locked" active-text="받기" inactive-text="막기"
                       inline-prompt @change="toggleEntry" />
            <el-button type="danger" plain size="small" class="end-button" @click="endNow">
              지금 종료
            </el-button>
          </p>
        </div>
      </div>

      <div class="board-head">
        <span>참가 {{ participants.length }}명</span>
        <span v-if="!homework.ended" class="muted">10초마다 저절로 바뀝니다</span>
      </div>
      <el-table v-loading="loading" :data="participants" class="full-width board" border size="small">
        <el-table-column label="번호" prop="number" width="70" fixed />
        <el-table-column label="닉네임" prop="nickname" min-width="100" fixed />
        <el-table-column label="4자리" prop="pin" width="70" />
        <el-table-column label="입장" width="70">
          <template #default="{ row }">{{ clock(row.join_time) }}</template>
        </el-table-column>
        <el-table-column label="마지막 제출" width="90">
          <template #default="{ row }">{{ row.last_submit_time ? clock(row.last_submit_time) : '-' }}</template>
        </el-table-column>
        <el-table-column v-for="(problem, index) in homework.problems" :key="problem.id"
                         min-width="110" align="center">
          <template #header>
            <el-tooltip :content="problem.title" placement="top">
              <span class="problem-head">{{ index + 1 }}. {{ problem.title }}</span>
            </el-tooltip>
            <div class="muted">정답 {{ problem.solved_count }}명</div>
          </template>
          <template #default="{ row }">
            <button v-if="row.cells[problem.id]" type="button"
                    :class="['cell', row.cells[problem.id].solved ? 'solved' : 'tried']"
                    @click="openCell(row, problem)">
              {{ row.cells[problem.id].solved ? '정답' : '오답' }} · {{ row.cells[problem.id].attempts }}회
            </button>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="관리" width="90" fixed="right">
          <template #default="{ row }">
            <el-dropdown trigger="click" @command="cmd => manage(cmd, row)">
              <el-button size="small">관리</el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="nickname">닉네임 바꾸기</el-dropdown-item>
                  <el-dropdown-item command="pin">4자리 숫자 바꾸기</el-dropdown-item>
                  <el-dropdown-item command="remove" divided>내보내기</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
        <template #empty>
          <span v-if="!loading">아직 들어온 학생이 없습니다. 코드를 크게 띄워 학생들에게 보여 주세요.</span>
        </template>
      </el-table>
    </Panel>

    <!-- 칠판·TV 에 띄우는 화면 -->
    <el-dialog v-model="showCode" fullscreen class="code-dialog" @open="drawQr">
      <div class="big">
        <p class="big-title">{{ homework.title }}</p>
        <p class="big-code">{{ homework.code }}</p>
        <img v-if="qr" :src="qr" alt="입장 QR 코드" class="qr" />
        <p class="big-link">{{ link }}</p>
        <p class="muted">oj.ssambox.com 첫 화면의 "바로 과제" 칸에 숫자를 넣어도 됩니다</p>
      </div>
    </el-dialog>

    <el-dialog v-model="deadlineVisible" title="마감 시각 바꾸기" width="400px">
      <el-date-picker v-model="deadline" type="datetime" format="YYYY-MM-DD HH:mm" :clearable="false" />
      <template #footer>
        <el-button @click="deadlineVisible = false">취소</el-button>
        <el-button type="primary" @click="saveDeadline">저장</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="cellVisible" :title="cellTitle" width="760px">
      <div v-loading="cellLoading">
        <div v-for="submission in cellSubmissions" :key="submission.id" class="submission">
          <div class="submission-head">
            <el-tag :type="statusOf(submission.result).type" size="small">
              {{ statusOf(submission.result).label }}
            </el-tag>
            <span>{{ localtime(submission.create_time, 'HH:mm:ss') }}</span>
            <span class="muted">{{ submission.language === 'Block Coding' ? '블록 코딩' : submission.language }}</span>
            <span v-if="submission.statistic_info.time_cost !== undefined" class="muted">
              {{ submission.statistic_info.time_cost }}ms
            </span>
          </div>
          <pre v-if="submission.statistic_info.err_info" class="err">{{ submission.statistic_info.err_info }}</pre>
          <BlocklyViewer v-if="submission.language === 'Block Coding' && submission.blockly_state"
                         :blocks="submission.blockly_state" />
          <Highlight v-else :code="submission.code" :language="submission.language" />
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, defineAsyncComponent } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@oj/api'
import time from '@/utils/time'
import { JUDGE_STATUS } from '@/utils/constants'
import Highlight from '@oj/components/Highlight.vue'
import { useAppStore } from '@/store/app'
const BlocklyViewer = defineAsyncComponent(() => import('@oj/components/BlocklyViewer.vue'))

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const homeworkId = Number(route.params.id)

const loading = ref(true)
const homework = ref({ problems: [], languages: [] })
const participants = ref([])
const link = computed(() => `${window.location.origin}/hw/${homework.value.code}`)

function localtime (value, fmt = 'M/D HH:mm') {
  return time.utcToLocal(value, fmt)
}

function clock (value) {
  return time.utcToLocal(value, 'HH:mm')
}

function statusOf (result) {
  return JUDGE_STATUS[result] || { label: '채점 중', type: 'info' }
}

// 남은 시간. 현황판을 10초마다 다시 불러오므로 그때 함께 바뀐다.
const nowMs = ref(Date.now())
const remaining = computed(() => {
  const minutes = Math.ceil((new Date(homework.value.end_time) - nowMs.value) / 60000)
  if (minutes <= 0) return '곧 종료'
  if (minutes < 60) return `${minutes}분 남음`
  if (minutes < 60 * 24) return `${Math.floor(minutes / 60)}시간 ${minutes % 60}분 남음`
  return `${Math.floor(minutes / 60 / 24)}일 남음`
})

let timer = null
function load () {
  return api.getHomeworkBoard(homeworkId).then(res => {
    homework.value = res.data.data.homework
    participants.value = res.data.data.participants
    nowMs.value = Date.now()
    appStore.changeDomTitle(homework.value.title)
    // 끝난 과제는 더 바뀌지 않는다
    if (homework.value.ended) clearInterval(timer)
  }, () => { clearInterval(timer) }).finally(() => { loading.value = false })
}

function copyLink () {
  navigator.clipboard.writeText(link.value).then(() => ElMessage.success('주소를 복사했습니다'),
    () => ElMessage.error('복사하지 못했습니다'))
}

// ---- 크게 보기 ----
const showCode = ref(false)
const qr = ref('')
function drawQr () {
  if (qr.value) return
  // QR 라이브러리는 이 화면에서만 쓴다. 띄울 때 내려받는다.
  import('qrcode').then(({ default: QRCode }) => QRCode.toDataURL(link.value, { width: 360, margin: 1 }))
    .then(url => { qr.value = url }, () => {})
}

// ---- 진행 바꾸기 ----
function edit (data, message) {
  return api.editHomework({ id: homeworkId, ...data }).then(() => {
    if (message) ElMessage.success(message)
    return load()
  }, () => {})
}

function editTitle () {
  ElMessageBox.prompt('새 제목', '제목 수정', { inputValue: homework.value.title,
    inputValidator: value => !!value.trim() || '제목을 입력하세요' })
    .then(({ value }) => edit({ title: value.trim() })).catch(() => {})
}

const deadlineVisible = ref(false)
const deadline = ref(null)
function openDeadline () {
  deadline.value = new Date(homework.value.end_time)
  deadlineVisible.value = true
}
function saveDeadline () {
  edit({ end_time: deadline.value.toISOString() }, '마감 시각을 바꿨습니다')
    .then(() => { deadlineVisible.value = false })
}

function toggleEntry (accept) {
  edit({ entry_locked: !accept }, accept ? '새 입장을 다시 받습니다' : '새 입장을 막았습니다. 이미 들어온 학생은 계속 들어올 수 있습니다')
}

function endNow () {
  ElMessageBox.confirm('지금 끝내면 더 제출할 수 없고, 새로 들어올 수도 없습니다. 다시 열 수 없습니다.',
    '과제 종료', { confirmButtonText: '종료', cancelButtonText: '취소', type: 'warning' })
    .then(() => edit({ end: true }, '과제를 종료했습니다')).catch(() => {})
}

// 결과 표만 담긴다(코드는 넣지 않는다). 문제집 학습 현황 엑셀과 같은 방식.
function download () {
  window.open(`/api/teacher/hw/board?id=${homeworkId}&download=1`)
}

function remove () {
  ElMessageBox.confirm(
    `"${homework.value.title}" 과제를 지웁니다. 참가한 학생 ${participants.value.length}명의 ` +
    '제출과 코드가 모두 지워지고 되돌릴 수 없습니다. 필요하면 먼저 엑셀로 내려받으세요.',
    '과제 삭제', { confirmButtonText: '삭제', cancelButtonText: '취소', type: 'warning' })
    .then(() => api.deleteHomework(homeworkId))
    .then(() => {
      ElMessage.success('과제를 지웠습니다')
      router.push({ name: 'teacher-homework-report' })
    }).catch(() => {})
}

// ---- 참가자 관리 ----
function manage (command, row) {
  const name = `${row.number}번 ${row.nickname}`
  if (command === 'nickname') {
    ElMessageBox.prompt(`${name}의 새 닉네임`, '닉네임 바꾸기', { inputValue: row.nickname,
      inputValidator: value => (!!value.trim() && value.length <= 20) || '1~20자로 넣어주세요' })
      .then(({ value }) => api.editHomeworkParticipant({ id: row.id, nickname: value.trim() }))
      .then(load).catch(() => {})
  } else if (command === 'pin') {
    ElMessageBox.prompt(`${name}의 새 4자리 숫자. 틀려서 잠겼다면 함께 풀립니다.`, '4자리 숫자 바꾸기',
      { inputPattern: /^\d{4}$/, inputErrorMessage: '숫자 4자리를 넣어주세요' })
      .then(({ value }) => api.editHomeworkParticipant({ id: row.id, pin: value }))
      .then(load).catch(() => {})
  } else if (command === 'remove') {
    ElMessageBox.confirm(`${name}을(를) 내보냅니다. 이 학생이 낸 코드와 결과가 모두 지워지고 번호가 빕니다.`,
      '내보내기', { confirmButtonText: '내보내기', cancelButtonText: '취소', type: 'warning' })
      .then(() => api.removeHomeworkParticipant(row.id)).then(load).catch(() => {})
  }
}

// ---- 칸 자세히 ----
const cellVisible = ref(false)
const cellLoading = ref(false)
const cellTitle = ref('')
const cellSubmissions = ref([])
function openCell (row, problem) {
  cellTitle.value = `${row.number}번 ${row.nickname} · ${problem.title}`
  cellSubmissions.value = []
  cellVisible.value = true
  cellLoading.value = true
  api.getHomeworkCellSubmissions(row.id, problem.id)
    .then(res => { cellSubmissions.value = res.data.data }, () => {})
    .finally(() => { cellLoading.value = false })
}

onMounted(() => {
  load().then(() => {
    if (route.query.created) showCode.value = true
  })
  timer = setInterval(() => {
    // 탭이 가려져 있으면 쉬었다가 다시 보일 때 받는다
    if (!document.hidden) load()
  }, 10 * 1000)
})
onBeforeUnmount(() => clearInterval(timer))
</script>

<style lang="less" scoped>
.title {
  margin-right: 8px;
}
.state {
  vertical-align: middle;
}
.muted {
  color: #909399;
  font-size: 12px;
}
.summary {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  margin-bottom: 20px;
}
.code-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 12px 24px;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  cursor: pointer;
  .code-label, .code-hint {
    font-size: 12px;
    color: #909399;
  }
  .code {
    font-size: 36px;
    font-weight: 700;
    letter-spacing: 4px;
  }
}
.facts {
  flex: 1 1 300px;
  min-width: 0;
  p {
    margin: 0 0 8px;
    overflow-wrap: anywhere;
  }
  .label {
    display: inline-block;
    width: 56px;
    color: #909399;
  }
  .controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
  }
}
.board-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 8px;
}
.problem-head {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: bottom;
}
.cell {
  border: none;
  border-radius: 4px;
  padding: 2px 8px;
  cursor: pointer;
  font-size: 12px;
  &.solved {
    background: #f0f9eb;
    color: #67c23a;
  }
  &.tried {
    background: #fdf6ec;
    color: #e6a23c;
  }
}
.big {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  .big-title {
    font-size: 28px;
    margin: 0;
  }
  .big-code {
    font-size: 120px;
    font-weight: 700;
    letter-spacing: 12px;
    margin: 16px 0;
    line-height: 1;
  }
  .qr {
    width: 300px;
    max-width: 80vw;
  }
  .big-link {
    font-size: 22px;
    overflow-wrap: anywhere;
  }
}
.submission {
  border-bottom: 1px solid #ebeef5;
  padding: 10px 0;
  .submission-head {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px;
    margin-bottom: 6px;
  }
  .err {
    background: #fef0f0;
    color: #f56c6c;
    padding: 8px;
    white-space: pre-wrap;
    font-size: 12px;
  }
}
@media (max-width: 600px) {
  .big .big-code {
    font-size: 64px;
    letter-spacing: 6px;
  }
}
</style>
