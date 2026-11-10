<template>
  <div class="hw-problem">
    <HomeworkHeader v-if="homework" :homework="homework" :participant="participant" @leave="leave" />

    <div v-if="problem" class="body">
      <el-button link :icon="ArrowLeft" class="back" @click="goList">문제 목록</el-button>

      <el-card class="statement">
        <h2>{{ problem.title }}</h2>
        <div class="markdown-body">
          <p class="title">문제 설명</p>
          <Markdown :source="problem.description" />
          <p class="title">입력</p>
          <Markdown :source="problem.input_description" />
          <p class="title">출력</p>
          <Markdown :source="problem.output_description" />
          <div v-for="(sample, index) of problem.samples" :key="index" class="sample">
            <div>
              <p class="title">입력 예제 {{ index + 1 }}</p>
              <pre>{{ sample.input }}</pre>
            </div>
            <div>
              <p class="title">출력 예제 {{ index + 1 }}</p>
              <pre>{{ sample.output }}</pre>
            </div>
          </div>
          <template v-if="problem.hint">
            <p class="title">힌트</p>
            <Markdown :source="problem.hint" />
          </template>
        </div>
      </el-card>

      <el-alert v-if="ended" type="info" show-icon :closable="false" class="notice"
                title="종료된 과제입니다. 더 낼 수 없고, 아래에서 내 제출 결과와 코드를 볼 수 있습니다" />

      <el-card v-else class="editor">
        <CodeMirror
          v-if="language !== 'Block Coding'"
          :value="code"
          :languages="textLanguages"
          :language="language"
          :theme="theme"
          :block-coding="allowBlock"
          @update:value="code = $event"
          @resetCode="resetCode"
          @changeTheme="theme = $event"
          @changeLang="changeLang"
        />
        <BlocklyEditor
          v-else
          :key="blocklyKey"
          :initial-blocks="blocklyState"
          :languages="textLanguages"
          @changeLang="changeLang"
          @input="blockCode = $event"
          @update:blocks="blocklyState = $event"
        />

        <div class="run-panel">
          <div class="run-head">
            <span class="run-title">입력</span>
            <el-button v-for="(sample, index) in problem.samples" :key="'sample' + index"
                       size="small" link type="primary" @click="runInput = sample.input">
              예제 {{ index + 1 }} 넣기
            </el-button>
          </div>
          <el-input v-model="runInput" type="textarea" :rows="3" resize="vertical"
                    placeholder="실행할 때 프로그램에 넣을 입력" />
          <div v-if="runResult" class="run-output">
            <div class="run-head">
              <span class="run-title">출력</span>
              <span v-if="runNotice" :class="['run-notice', { bad: runResult.result !== 'ok' }]">
                {{ runNotice }}
              </span>
            </div>
            <pre v-if="runText !== null">{{ runText }}</pre>
          </div>
        </div>

        <div class="actions">
          <div class="status">
            <template v-if="lastResult">
              <span>결과</span>
              <el-tag :type="statusOf(lastResult.result).type">{{ statusOf(lastResult.result).label }}</el-tag>
            </template>
          </div>
          <div>
            <el-button :loading="running" @click="runCode">{{ running ? '실행 중' : '실행' }}</el-button>
            <el-button type="warning" :loading="submitting" @click="submitCode">
              {{ submitting ? '채점 중' : '제출' }}
            </el-button>
          </div>
        </div>
      </el-card>

      <el-card class="history">
        <template #header><span class="card-title">내 제출 ({{ submissions.length }})</span></template>
        <el-table :data="submissions" empty-text="아직 낸 코드가 없습니다" row-key="id">
          <el-table-column type="expand">
            <template #default="{ row }">
              <div class="submitted-code">
                <BlocklyViewer v-if="row.language === 'Block Coding' && row.blockly_state"
                               :blocks="row.blockly_state" />
                <Highlight v-else :code="row.code" :language="row.language" />
                <el-button v-if="!ended" size="small" @click="loadIntoEditor(row)">
                  이 코드를 편집기로 불러오기
                </el-button>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="낸 시각" min-width="90">
            <template #default="{ row }">{{ localtime(row.create_time) }}</template>
          </el-table-column>
          <el-table-column label="언어" min-width="90">
            <template #default="{ row }">{{ row.language === 'Block Coding' ? '블록 코딩' : row.language }}</template>
          </el-table-column>
          <el-table-column label="결과" min-width="100">
            <template #default="{ row }">
              <el-tag :type="statusOf(row.result).type">{{ statusOf(row.result).label }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="시간" min-width="70">
            <template #default="{ row }">
              {{ row.statistic_info.time_cost !== undefined ? row.statistic_info.time_cost + 'ms' : '-' }}
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, defineAsyncComponent } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import Markdown from '@oj/components/Markdown.vue'
import Highlight from '@oj/components/Highlight.vue'
import api from '@oj/api'
import time from '@/utils/time'
import { JUDGE_STATUS } from '@/utils/constants'
import { useAppStore } from '@/store/app'
import HomeworkHeader from './HomeworkHeader.vue'
// 편집기는 한 번에 하나만 쓰이고 각각 수백 KB 다. 실제로 쓰는 쪽만 내려받는다.
const CodeMirror = defineAsyncComponent(() => import('@oj/components/CodeMirror.vue'))
const BlocklyEditor = defineAsyncComponent(() => import('@oj/components/BlocklyEditor.vue'))
const BlocklyViewer = defineAsyncComponent(() => import('@oj/components/BlocklyViewer.vue'))

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const hwCode = route.params.code
const problemId = Number(route.params.problemId)

const homework = ref(null)
const participant = ref(null)
const problem = ref(null)
const submissions = ref([])

const language = ref('')
// 글 편집기의 코드. 블록이 만든 코드는 blockCode 에 따로 둔다.
// 하나로 쓰면 블록 편집기가 열리는 순간 쓰던 파이썬 코드를 덮어쓴다.
const code = ref('')
const blockCode = ref('')
const blocklyState = ref('')
// 블록 편집기는 처음 띄울 때만 블록을 읽는다. 불러오기를 하면 새로 띄운다.
const blocklyKey = ref(0)
const theme = ref('solarized')

// 실행·제출할 코드
const editorCode = computed(() => language.value === 'Block Coding' ? blockCode.value : code.value)
const ended = computed(() => !homework.value || homework.value.ended)
const allowBlock = computed(() => problem.value.languages.includes('Block Coding'))
const textLanguages = computed(() => problem.value.languages.filter(l => l !== 'Block Coding'))

function statusOf (result) {
  return JUDGE_STATUS[result] || { label: '채점 중', type: 'info' }
}

function localtime (value) {
  return time.utcToLocal(value, 'M/D HH:mm:ss')
}

function goList () {
  router.push({ name: 'homework-home', params: { code: hwCode } })
}

function leave () {
  api.leaveHomework(hwCode).then(goList, () => {})
}

// 입장하지 않았으면 입장 화면으로 보낸다
function backToJoin (res) {
  if (res?.data?.error === 'hw-join-required') goList()
}

function template (lang) {
  return problem.value.template?.[lang] || ''
}

// 마지막으로 낸 코드로 이어서 푼다. 낸 적이 없으면 블록 코딩(되면) 또는 첫 언어로 시작한다.
function startEditor () {
  const last = problem.value.last_submission
  if (last && problem.value.languages.includes(last.language)) {
    loadIntoEditor(last, false)
    return
  }
  language.value = allowBlock.value ? 'Block Coding' : textLanguages.value[0]
  code.value = template(language.value)
}

function loadIntoEditor (submission, notify = true) {
  language.value = submission.language
  if (submission.language === 'Block Coding') {
    // 블록 코드는 블록 편집기가 블록에서 다시 만든다. 글 편집기의 코드는 건드리지 않는다.
    blocklyState.value = submission.blockly_state || ''
    blocklyKey.value++
  } else {
    code.value = submission.code
  }
  if (notify) ElMessage.success('편집기로 불러왔습니다')
}

// 손대지 않은 코드: 비었거나 어느 언어의 템플릿 그대로.
function isUntouched (text) {
  return !text.trim() || Object.values(problem.value.template || {}).includes(text)
}

function changeLang (lang) {
  if (lang !== 'Block Coding' && isUntouched(code.value)) {
    // 블록에서 파이썬으로 넘어가면 블록이 만든 코드로 이어서 쓸 수 있게 한다.
    // 이미 쓰던 파이썬 코드가 있으면 그대로 둔다.
    code.value = language.value === 'Block Coding' && lang === 'Python3' && blockCode.value.trim()
      ? blockCode.value
      : template(lang)
  }
  language.value = lang
}

function resetCode () {
  ElMessageBox.confirm('코드를 초기화하시겠습니까?', '확인').then(() => {
    code.value = template(language.value)
  }).catch(() => {})
}

function loadSubmissions () {
  return api.getHomeworkSubmissions(hwCode, problemId).then(res => {
    submissions.value = res.data.data
  }, () => {})
}

// ---- 실행 ----
const runInput = ref('')
const running = ref(false)
const runResult = ref(null)
let runTimer = null

const runText = computed(() => {
  const r = runResult.value
  if (!r) return null
  if (r.result === 'compile_error') return r.message
  if (r.output === undefined) return null
  return r.output === '' ? '(출력 없음)' : r.output
})

const runNotice = computed(() => {
  const r = runResult.value
  if (!r) return ''
  switch (r.result) {
    case 'ok': return r.truncated ? '출력이 길어 앞부분만 보여줍니다' : ''
    case 'compile_error': return '컴파일되지 않습니다'
    case 'runtime_error': return '실행 중 오류가 났습니다. 아래 메시지를 확인하세요'
    // 가장 흔한 경우: input() 이 입력을 기다리다 시간이 다 된다
    case 'time_limit': return runInput.value.trim()
      ? '시간이 초과했습니다'
      : '시간이 초과했습니다. 입력을 기다리다 끝났을 수 있습니다 - 입력 칸을 채워보세요'
    case 'memory_limit': return '메모리가 초과했습니다'
    default: return r.message || '실행하지 못했습니다'
  }
})

function runCode () {
  if (editorCode.value.trim() === '') {
    ElMessage.error('코드가 비어있습니다')
    return
  }
  clearTimeout(runTimer)
  running.value = true
  runResult.value = null
  api.runHomework(hwCode, {
    problem_id: problemId, language: language.value, code: editorCode.value, input: runInput.value
  }).then(res => pollRun(res.data.data.token), () => { running.value = false })
}

function pollRun (token) {
  runTimer = setTimeout(() => {
    api.getHomeworkRun(hwCode, token).then(res => {
      if (res.data.data.status !== 'done') {
        pollRun(token)
        return
      }
      running.value = false
      runResult.value = res.data.data
    }, () => { running.value = false })
  }, 1000)
}

// ---- 제출 ----
const submitting = ref(false)
const lastResult = ref(null)
let submitTimer = null

function submitCode () {
  if (editorCode.value.trim() === '') {
    ElMessage.error('코드가 비어있습니다')
    return
  }
  submitting.value = true
  lastResult.value = null
  api.submitHomework(hwCode, {
    problem_id: problemId,
    language: language.value,
    code: editorCode.value,
    blockly_state: language.value === 'Block Coding' ? blocklyState.value : ''
  }).then(res => {
    loadSubmissions()
    pollSubmission(res.data.data.submission_id)
  }, () => { submitting.value = false })
}

// 채점이 끝나면 statistic_info 가 채워진다(일반 문제 화면과 같은 판단)
function pollSubmission (id) {
  submitTimer = setTimeout(() => {
    api.getHomeworkSubmission(hwCode, id).then(res => {
      const submission = res.data.data
      if (Object.keys(submission.statistic_info).length === 0) {
        pollSubmission(id)
        return
      }
      submitting.value = false
      lastResult.value = submission
      loadSubmissions()
    }, () => { submitting.value = false })
  }, 2000)
}

onMounted(() => {
  api.getHomeworkMe(hwCode).then(res => {
    homework.value = res.data.data.homework
    participant.value = res.data.data.participant
  }, backToJoin)
  api.getHomeworkProblem(hwCode, problemId).then(res => {
    problem.value = res.data.data
    appStore.changeDomTitle(problem.value.title)
    startEditor()
    loadSubmissions()
  }, backToJoin)
})

onBeforeUnmount(() => {
  clearTimeout(runTimer)
  clearTimeout(submitTimer)
})
</script>

<style lang="less" scoped>
// 바로 과제 화면은 모두 같은 폭(문제 목록과 같게)
.hw-problem {
  max-width: 1000px;
  margin: 0 auto;
}
// 링크 버튼의 안쪽 여백을 지워 아래 카드의 왼쪽 끝과 맞춘다
.back {
  height: auto;
  padding: 0;
  margin-bottom: 10px;
  font-size: 14px;
}
.statement, .editor, .notice, .history {
  margin-bottom: 16px;
}
.statement {
  h2 {
    margin: 0 0 12px;
    overflow-wrap: anywhere;
  }
  .title {
    font-weight: 600;
    margin: 18px 0 6px;
  }
  .sample {
    display: flex;
    flex-wrap: wrap;
    gap: 0 16px;
    > div {
      flex: 1 1 240px;
      min-width: 0;
    }
  }
  pre {
    background: #f5f7fa;
    padding: 8px 12px;
    overflow-x: auto;
  }
}
.run-panel {
  margin-top: 12px;
  .run-head {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
  }
  .run-title {
    font-weight: 600;
  }
  .run-notice {
    color: #67c23a;
    &.bad {
      color: #f56c6c;
    }
  }
  .run-output {
    margin-top: 12px;
    pre {
      background: #f5f7fa;
      padding: 8px 12px;
      max-height: 300px;
      overflow: auto;
      margin: 0;
    }
  }
}
.actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 16px;
  .status {
    display: flex;
    align-items: center;
    gap: 8px;
  }
}
.card-title {
  font-weight: 600;
}
.submitted-code {
  padding: 0 16px 8px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
  > :first-child {
    width: 100%;
  }
}
</style>
