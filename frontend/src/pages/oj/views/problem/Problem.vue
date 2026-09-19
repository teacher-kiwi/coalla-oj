<template>
  <div class="flex-container">
    <div id="problem-main">
        <Panel :padding="40" shadow>
        <template #title>{{ problem.title }}</template>
        <div v-if="problemLoaded" id="problem-content" class="markdown-body">
          <p class="title">문제 설명</p>
          <Markdown class="content" :source="problem.description" />

          <p class="title">
            입력
            <span v-if="problem.io_mode.io_mode == 'File IO'">(파일 입력: {{ problem.io_mode.input }})</span>
          </p>
          <Markdown class="content" :source="problem.input_description" />

          <p class="title">
            출력
            <span v-if="problem.io_mode.io_mode == 'File IO'">(파일 출력: {{ problem.io_mode.output }})</span>
          </p>
          <Markdown class="content" :source="problem.output_description" />

          <div v-for="(sample, index) of problem.samples" :key="index">
            <div class="flex-container sample">
              <div class="sample-input">
                <p class="title">
                  입력 예제 {{ index + 1 }}
                  <a class="copy" @click="copyToClipboard(sample.input)">
                    <el-icon><DocumentCopy /></el-icon>
                  </a>
                </p>
                <pre>{{ sample.input }}</pre>
              </div>
              <div class="sample-output">
                <p class="title">출력 예제 {{ index + 1 }}</p>
                <pre>{{ sample.output }}</pre>
              </div>
            </div>
          </div>

          <div v-if="problem.hint">
            <p class="title">힌트</p>
            <el-card>
              <Markdown class="content" :source="problem.hint" />
            </el-card>
          </div>

          <div v-if="problem.source">
            <p class="title">출처</p>
            <p class="content">{{ problem.source }}</p>
          </div>
        </div>
      </Panel>
  
      <el-card :body-style="{ padding: '20px' }" id="submit-code">
        <CodeMirror
          v-if="language !== 'Block Coding'"
          :value="code"
          :languages="problem.languages"
          :language="language"
          :theme="theme"
          @update:value="code = $event"
          @resetCode="onResetToTemplate"
          @changeTheme="onChangeTheme"
          @changeLang="onChangeLang"
        />

        <BlocklyEditor
          v-else
          :initial-blocks="blocklyWorkspace"
          :languages="problem.languages"
          @changeLang="onChangeLang"
          @input="onCodeGenerated"
          @update:blocks="onWorkspaceChanged"
        />

        <!-- 제출하기 전에 자기 입력으로 돌려 보고 print 로 중간 값을 찍어 보는 자리.
             제출이 아니라 기록·통계에 남지 않는다(judge/run.py). -->
        <div class="run-panel">
          <div class="run-head">
            <span class="run-title">입력</span>
            <el-button v-for="(sample, index) in (problem.samples || [])" :key="'run-sample' + index"
                       size="small" link type="primary" @click="runInput = sample.input">
              예제 {{ index + 1 }} 넣기
            </el-button>
          </div>
          <el-input v-model="runInput" type="textarea" :rows="3" resize="vertical"
                    placeholder="실행할 때 프로그램에 넣을 입력" class="run-input" />

          <div v-if="runResult" class="run-output">
            <div class="run-head">
              <span class="run-title">출력</span>
              <span v-if="runMeta" class="run-meta">{{ runMeta }}</span>
              <span v-if="sampleMatch !== null" :class="['run-match', { bad: !sampleMatch }]">
                예제 {{ ranSample }}의 출력과 {{ sampleMatch ? '같습니다' : '다릅니다' }}
              </span>
            </div>
            <p v-if="runNotice" :class="['run-notice', { bad: runResult.result !== 'ok' }]">
              {{ runNotice }}
            </p>
            <pre v-if="runText !== null" class="run-pre">{{ runText }}</pre>
          </div>
        </div>

        <el-row justify="space-between">
          <el-col :span="10">
            <div class="status" v-if="statusVisible">
              <template v-if="!contestID || (contestID && OIContestRealTimePermission)">
                <span>상태</span>
                <el-tag :type="submissionStatus.type" @click="handleRoute('/status/' + submissionId)" class="status-tag">
                  {{ submissionStatus.label }}
                </el-tag>
              </template>
              <template v-else-if="contestID && !OIContestRealTimePermission">
                <el-alert type="success" show-icon :closable="false">제출 완료</el-alert>
              </template>
            </div>
            <div v-else-if="problem.my_status === 0">
              <el-alert type="success" show-icon :closable="false">문제를 해결했습니다</el-alert>
            </div>
            <div v-else-if="contestID && !OIContestRealTimePermission && submissionExists">
              <el-alert type="success" show-icon :closable="false">솔루션을 제출했습니다.</el-alert>
            </div>
            <div v-if="contestEnded">
              <el-alert type="warning" show-icon :closable="false">대회가 종료되었습니다</el-alert>
            </div>
          </el-col>

          <el-col :span="12">
            <el-button type="warning" :loading="submitting" @click="submitCode"
                       :disabled="problemSubmitDisabled || submitted" class="fl-right">
              <span v-if="submitting">제출 중</span>
              <span v-else>제출</span>
            </el-button>
            <el-button :loading="running" @click="runCode"
                       :disabled="problemSubmitDisabled" class="fl-right run-button">
              {{ running ? '실행 중' : '실행' }}
            </el-button>
          </el-col>
        </el-row>
      </el-card>
    </div>

    <div id="right-column">
      <VerticalMenu @on-click="handleRoute">
        <template v-if="contestID">
          <VerticalMenuItem :route="{ name: 'contest-problem-list', params: { contestID } }">
            <el-icon><PictureFilled /></el-icon>
            문제
          </VerticalMenuItem>
          <VerticalMenuItem :route="{ name: 'contest-announcement-list', params: { contestID } }">
            <el-icon><ChatDotRound /></el-icon>
            공지
          </VerticalMenuItem>
        </template>

        <VerticalMenuItem v-if="!contestID || OIContestRealTimePermission" :route="submissionRoute">
          <el-icon><List /></el-icon>
          제출
        </VerticalMenuItem>

        <template v-if="contestID">
          <VerticalMenuItem v-if="!contestID || OIContestRealTimePermission"
                            :route="{ name: 'contest-rank', params: { contestID } }">
            <el-icon><TrendCharts /></el-icon>
            순위
          </VerticalMenuItem>
          <VerticalMenuItem :route="{ name: 'contest-details', params: { contestID } }">
            <el-icon><House /></el-icon>
            대회 보기
          </VerticalMenuItem>
        </template>
      </VerticalMenu>

      <el-card id="info">
        <template #header>
          <div class="header icon-label">
            <el-icon><InfoFilled /></el-icon>
            <span class="card-title">정보</span>
          </div>
        </template>
        <ul>
          <li><p>ID</p><p>{{ problem.display_id }}</p></li>
          <li><p>시간 제한</p><p>{{ problem.time_limit }}MS</p></li>
          <li><p>메모리 제한</p><p>{{ problem.memory_limit }}MB</p></li>
          <li><p>IO 모드</p><p>{{ problem.io_mode.io_mode }}</p></li>
          <!-- 출제 교사가 탈퇴해도 공개 문제는 남는다(created_by 가 null 이 된다) -->
          <li><p>작성자</p><p>{{ problem.created_by?.username || '(삭제된 사용자)' }}</p></li>
          <li v-if="problem.difficulty"><p>난이도</p><p>{{ DIFFICULTY_LABEL[problem.difficulty] }}</p></li>
          <li v-if="!contestID && userStore.isAuthenticated">
            <p>즐겨찾기</p>
            <p><FavoriteHeart :on="!!problem.my_favorite" @toggle="toggleFavorite" /></p>
          </li>
          <li v-if="problem.total_score"><p>점수</p><p>{{ problem.total_score }}</p></li>
          <li>
            <p>태그</p>
            <p>
              <el-popover trigger="hover" placement="left-end">
                <template #reference><a>보기</a></template>
                <el-tag v-for="tag in problem.tags" :key="tag" class="info-tag">{{ tag }}</el-tag>
              </el-popover>
            </p>
          </li>
        </ul>
      </el-card>

      <el-card id="pieChart" :body-style="{ padding: 0 }" v-if="!contestID || OIContestRealTimePermission">
        <template #header>
          <div class="chart-header icon-label">
            <el-icon><DataAnalysis /></el-icon>
            <span class="card-title">통계</span>
            <el-button size="small" id="detail" @click="graphVisible = !graphVisible">자세히</el-button>
          </div>
        </template>
        <div class="echarts">
          <VChart :option="pie" autoresize />
        </div>
      </el-card>
    </div>

    <el-dialog v-model="graphVisible">
      <div id="pieChart-detail">
        <VChart :option="largePie" autoresize class="large-pie-chart" />
      </div>
      <template #footer>
        <el-button @click="graphVisible = false">닫기</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, defineAsyncComponent } from 'vue'
import Markdown from '@oj/components/Markdown.vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  DocumentCopy, PictureFilled, ChatDotRound, List, TrendCharts, House,
  InfoFilled, DataAnalysis
} from '@element-plus/icons-vue'
// 두 에디터는 한 번에 하나만 쓰이고 각각 수백 KB 다. 실제로 선택된 쪽만 내려받는다.
const CodeMirror = defineAsyncComponent(() => import('@oj/components/CodeMirror.vue'))
const BlocklyEditor = defineAsyncComponent(() => import('@oj/components/BlocklyEditor.vue'))
import VerticalMenu from '@oj/components/verticalMenu/verticalMenu.vue'
import VerticalMenuItem from '@oj/components/verticalMenu/verticalMenu-item.vue'
import storage from '@/utils/storage'
import { JUDGE_STATUS, CONTEST_STATUS, buildProblemCodeKey, DIFFICULTY_LABEL } from '@/utils/constants'
import api from '@oj/api'
import FavoriteHeart from '@oj/components/FavoriteHeart.vue'
import { pie as pieData, largePie as largePieData } from './chartData'
import { useContestStore } from '@/store/contest'
import { useAppStore } from '@/store/app'
import { useUserStore } from '@/store/user'

function structuredCloneWithFunctions (obj) {
  if (obj === null || typeof obj !== 'object') return obj
  if (Array.isArray(obj)) return obj.map(structuredCloneWithFunctions)
  const clone = {}
  for (const key in obj) {
    clone[key] = typeof obj[key] === 'function' ? obj[key] : structuredCloneWithFunctions(obj[key])
  }
  return clone
}

const filtedStatus = ['-1', '-2', '0', '1', '2', '3', '4', '8']

const route = useRoute()
const router = useRouter()
const contestStore = useContestStore()
const appStore = useAppStore()
const userStore = useUserStore()

const statusVisible = ref(false)
const graphVisible = ref(false)
const submissionExists = ref(false)
const contestID = ref('')
const problemID = ref('')
const submitting = ref(false)
const code = ref('')
const language = ref('C++')
const theme = ref('solarized')
const submissionId = ref('')
const submitted = ref(false)
const blocklyWorkspace = ref('')
const result = ref({ result: 9 })
const problemLoaded = ref(false)
const problem = ref({
  title: '',
  description: '',
  hint: '',
  my_status: '',
  my_favorite: false,
  template: {},
  languages: [],
  created_by: null,
  tags: [],
  io_mode: { io_mode: 'Standard IO' }
})
const pie = ref(structuredCloneWithFunctions(pieData))
const largePie = ref(structuredCloneWithFunctions(largePieData))

// 화면에서 먼저 뒤집고 서버에 알린다. 실패하면 되돌린다.
function toggleFavorite () {
  const next = !problem.value.my_favorite
  problem.value.my_favorite = next
  const request = next ? api.addProblemFavorite(problem.value.display_id)
                       : api.removeProblemFavorite(problem.value.display_id)
  request.catch(() => { problem.value.my_favorite = !next })
}

let refreshStatus = null

const OIContestRealTimePermission = computed(() => contestStore.OIContestRealTimePermission)
const problemSubmitDisabled = computed(() => contestStore.problemSubmitDisabled)
const contestRuleType = computed(() => contestStore.contestRuleType)
const contestStatusVal = computed(() => contestStore.contestStatus)

const contestEnded = computed(() => contestStatusVal.value === CONTEST_STATUS.ENDED)

const submissionStatus = computed(() => ({
  text: JUDGE_STATUS[result.value.result]['name'],
  label: JUDGE_STATUS[result.value.result]['label'],
  color: JUDGE_STATUS[result.value.result]['color'],
  type: JUDGE_STATUS[result.value.result]['type']
}))

const submissionRoute = computed(() => {
  if (contestID.value) {
    return { name: 'contest-submission-list', query: { problemID: problemID.value } }
  }
  return { name: 'submission-list', query: { problemID: problemID.value } }
})

function copyToClipboard (text) {
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('복사했습니다')
  }).catch(() => {
    ElMessage.error('복사에 실패했습니다')
  })
}

function init () {
  contestStore.changeContestItemVisible({ menu: false })
  contestID.value = route.params.contestID || ''
  problemID.value = route.params.problemID || ''

  const func = route.name === 'problem-details' ? 'getProblem' : 'getContestProblem'
  api[func](problemID.value, contestID.value).then(res => {
    const prob = res.data.data
    appStore.changeDomTitle(prob.title)
    api.submissionExists(prob.id, contestID.value).then(r => {
      submissionExists.value = r.data.data
    })
    prob.languages = prob.languages.sort()
    problemLoaded.value = false
    problem.value = prob
    if (prob.statistic_info) changePie(prob)
    problemLoaded.value = true

    // 저장해둔 코드가 있으면 불러온다
    const savedCode = storage.get(buildProblemCodeKey(route.params.problemID, route.params.contestID))
    if (savedCode) {
      language.value = savedCode.language
      code.value = savedCode.code
      theme.value = savedCode.theme
      if (savedCode.blocklyState) blocklyWorkspace.value = savedCode.blocklyState
      return
    }

    if (code.value !== '') return

    if (prob.languages.includes('Python3')) {
      language.value = 'Block Coding'
    } else {
      language.value = prob.languages[0]
    }
    const template = prob.template
    if (template && template[language.value]) {
      code.value = template[language.value]
    }
  }, () => {})
}

function changePie (problemData) {
  for (const k in problemData.statistic_info) {
    if (filtedStatus.indexOf(k) === -1) {
      delete problemData.statistic_info[k]
    }
  }
  const acNum = problemData.accepted_number
  const data = [
    { name: 'WA', value: problemData.submission_number - acNum },
    { name: 'AC', value: acNum }
  ]
  pie.value.series[0].data = data
  const data2 = JSON.parse(JSON.stringify(data))
  data2[1].selected = true
  largePie.value.series[1].data = data2

  const legend = Object.keys(problemData.statistic_info).map(ele => JUDGE_STATUS[ele].short)
  if (legend.length === 0) legend.push('AC', 'WA')
  largePie.value.legend.data = legend

  const acCount = problemData.statistic_info['0']
  delete problemData.statistic_info['0']

  const lpData = []
  Object.keys(problemData.statistic_info).forEach(ele => {
    lpData.push({ name: JUDGE_STATUS[ele].short, value: problemData.statistic_info[ele] })
  })
  lpData.push({ name: 'AC', value: acCount })
  largePie.value.series[0].data = lpData
}

function handleRoute (routeObj) {
  router.push(routeObj)
}

function onChangeLang (newLang) {
  if (problem.value.template[newLang]) {
    if (code.value.trim() === '') {
      code.value = problem.value.template[newLang]
    }
  }
  language.value = newLang
}

function onChangeTheme (newTheme) {
  theme.value = newTheme
}

function onResetToTemplate () {
  ElMessageBox.confirm('코드를 초기화하시겠습니까?', '확인').then(() => {
    const template = problem.value.template
    if (template && template[language.value]) {
      code.value = template[language.value]
    } else {
      code.value = ''
    }
  }).catch(() => {})
}

function onCodeGenerated (newCode) {
  code.value = newCode
}

function onWorkspaceChanged (workspaceJson) {
  blocklyWorkspace.value = workspaceJson
}

function checkSubmissionStatus () {
  if (refreshStatus) clearTimeout(refreshStatus)
  const checkStatus = () => {
    const id = submissionId.value
    api.getSubmission(id).then(res => {
      result.value = res.data.data
      if (Object.keys(res.data.data.statistic_info).length !== 0) {
        submitting.value = false
        submitted.value = false
        clearTimeout(refreshStatus)
        init()
      } else {
        refreshStatus = setTimeout(checkStatus, 2000)
      }
    }, () => {
      submitting.value = false
      clearTimeout(refreshStatus)
    })
  }
  refreshStatus = setTimeout(checkStatus, 2000)
}

// ---- 실행 ----
const runInput = ref('')
const running = ref(false)
const runResult = ref(null)
// 실행한 그 순간의 입력. 결과를 보는 동안 입력 칸을 고쳐도 판단이 흔들리지 않게 따로 둔다.
const ranInput = ref('')
let runTimer = null

// 채점기와 같은 기준으로 견준다: 출력 끝의 공백·줄바꿈만 무시한다.
// (줄마다 끝 공백을 지우면 화면은 "같습니다" 인데 채점은 오답인 경우가 생긴다)
function sameText (a, b) {
  const clean = text => (text || '').replace(/\r\n/g, '\n').trimEnd()
  return clean(a) === clean(b)
}

// 넣은 입력이 예제와 같으면 몇 번 예제인지
const ranSample = computed(() => {
  const index = (problem.value.samples || []).findIndex(s => sameText(s.input, ranInput.value))
  return index < 0 ? null : index + 1
})

// 스페셜 저지는 정답이 여럿이라 예제 출력과 달라도 맞을 수 있어 견주지 않는다
const sampleMatch = computed(() => {
  if (!runResult.value || runResult.value.result !== 'ok') return null
  if (!ranSample.value || problem.value.spj) return null
  return sameText(runResult.value.output, problem.value.samples[ranSample.value - 1].output)
})

const runMeta = computed(() => {
  const r = runResult.value
  if (!r || r.time === undefined || r.time === null) return ''
  return `${r.time}ms · ${(r.memory / 1024 / 1024).toFixed(1)}MB`
})

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
    case 'time_limit': return ranInput.value.trim()
      ? '시간이 초과했습니다'
      : '시간이 초과했습니다. 입력을 기다리다 끝났을 수 있습니다 - 입력 칸을 채워보세요'
    case 'memory_limit': return '메모리가 초과했습니다'
    default: return r.message || '실행하지 못했습니다'
  }
})

function runCode () {
  if (code.value.trim() === '') {
    ElMessage.error('코드가 비어있습니다')
    return
  }
  clearTimeout(runTimer)
  running.value = true
  runResult.value = null
  ranInput.value = runInput.value
  const data = {
    problem_id: problem.value.id,
    language: language.value,
    code: code.value,
    input: runInput.value
  }
  if (contestID.value) data.contest_id = contestID.value
  api.runCode(data).then(res => pollRun(res.data.data.token), () => {
    running.value = false
  })
}

function pollRun (token) {
  runTimer = setTimeout(() => {
    api.getRunResult(token).then(res => {
      const record = res.data.data
      if (record.status !== 'done') {
        pollRun(token)
        return
      }
      running.value = false
      runResult.value = record
    }, () => {
      running.value = false
    })
  }, 1000)
}

// 화면을 떠나면 결과는 필요 없다. 캐시에 남은 것은 시간이 지나 사라진다.
onBeforeUnmount(() => clearTimeout(runTimer))

function submitCode () {
  if (code.value.trim() === '') {
    ElMessage.error('코드가 비어있습니다')
    return
  }
  submissionId.value = ''
  result.value = { result: 9 }
  submitting.value = true

  const data = {
    problem_id: problem.value.id,
    language: language.value,
    code: code.value,
    blockly_state: language.value === 'Block Coding' ? blocklyWorkspace.value : ''
  }
  // 대회 문제가 아니면 키 자체를 넣지 않는다. 빈 문자열을 보내면
  // IntegerField(required=False) 가 "A valid integer is required" 로 거절한다.
  if (contestID.value) {
    data.contest_id = contestID.value
  }

  const submitFunc = (d, detailsVisible) => {
    statusVisible.value = true
    api.submitCode(d).then(res => {
      submissionId.value = res.data.data && res.data.data.submission_id
      submitting.value = false
      submissionExists.value = true
      if (!detailsVisible) {
        ElMessageBox.alert('코드 제출 성공', '성공')
        return
      }
      submitted.value = true
      checkSubmissionStatus()
    }, () => {
      submitting.value = false
      statusVisible.value = false
    })
  }

  if (contestRuleType.value === 'OI' && !OIContestRealTimePermission.value) {
    if (submissionExists.value) {
      ElMessageBox.confirm('이 문제에 제출 내역이 있습니다. 덮어쓰시겠습니까?', '').then(() => {
        setTimeout(() => submitFunc(data, false), 1000)
      }).catch(() => {
        submitting.value = false
      })
    } else {
      submitFunc(data, false)
    }
  } else {
    submitFunc(data, true)
  }
}

onMounted(() => {
  init()
})

onBeforeRouteLeave((to, from) => {
  clearTimeout(refreshStatus)
  contestStore.changeContestItemVisible({ menu: true })
  storage.set(buildProblemCodeKey(problem.value.display_id, from.params.contestID), {
    code: code.value,
    language: language.value,
    theme: theme.value,
    blocklyState: language.value === 'Block Coding' ? blocklyWorkspace.value : ''
  })
})

onBeforeUnmount(() => {
  clearTimeout(refreshStatus)
})

watch(() => route.fullPath, () => {
  init()
})
</script>

<style lang="less" scoped>
.run-panel {
  margin: 12px 0;
}

.run-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.run-title {
  font-size: 13px;
  font-weight: 600;
  color: #606266;
}

.run-output {
  margin-top: 12px;
}

.run-meta {
  font-size: 12px;
  color: #909399;
}

.run-match {
  font-size: 12px;
  color: #67c23a;

  &.bad {
    color: #e6a23c;
  }
}

.run-notice {
  margin: 0 0 6px;
  font-size: 13px;
  color: #606266;

  &.bad {
    color: #e6a23c;
  }
}

.run-pre {
  margin: 0;
  padding: 10px 12px;
  max-height: 320px;
  overflow: auto;
  background: #f5f7fa;
  border-radius: 4px;
  font-family: Consolas, Monaco, "Courier New", monospace;
  font-size: 13px;
  white-space: pre-wrap;
  word-break: break-all;
}

.run-button {
  margin-right: 10px;
}

.flex-container {
  #problem-main {
    flex: auto;
    margin-right: 18px;
    // 긴 코드 블록이나 넓은 표가 본문에 들어오면 이 칸의 최소 폭이 그만큼 커진다.
    // 풀어두지 않으면 창을 줄여도 칸이 버티고 화면 전체에 가로 스크롤이 생긴다.
    // (submission/SubmissionList.vue 에 같은 설명이 있다)
    min-width: 0;
  }
  #right-column {
    flex: none;
    width: 220px;
  }
}

#problem-content {
  margin-top: -50px;
  .title {
    font-size: 20px;
    font-weight: 400;
    margin: 25px 0 8px 0;
    color: #3091f2;
    .copy {
      padding-left: 8px;
      cursor: pointer;
    }
  }
  p.content {
    margin-left: 25px;
    margin-right: 20px;
    font-size: 15px;
  }
  .sample {
    align-items: stretch;
    &-input,
    &-output {
      width: 50%;
      flex: 1 1 auto;
      display: flex;
      flex-direction: column;
      margin-right: 5%;
    }
    pre {
      flex: 1 1 auto;
      align-self: stretch;
      border-style: solid;
      background: transparent;
    }
  }
}

#submit-code {
  margin-top: 20px;
  margin-bottom: 20px;
  .status {
    float: left;
    span {
      margin-right: 10px;
      margin-left: 10px;
    }
  }
}

#info {
  margin-bottom: 20px;
  margin-top: 20px;
  ul {
    margin: 0;
    padding: 0;
    list-style-type: none;
    li {
      border-bottom: 1px dotted #e9eaec;
      margin-bottom: 10px;
      p {
        display: inline-block;
      }
      p:first-child {
        width: 90px;
      }
      p:last-child {
        float: right;
      }
    }
  }
}

.fl-right {
  float: right;
}

.status-tag {
  cursor: pointer;
}

.info-tag {
  margin-right: 4px;
}

.chart-header {
  position: relative;
}

#pieChart {
  .echarts {
    height: 250px;
    width: 210px;
  }
  #detail {
    position: absolute;
    right: 10px;
    top: 10px;
  }
}

#pieChart-detail {
  margin: 20px auto 0;
  width: 500px;
  height: 480px;
}

.large-pie-chart {
  width: 500px;
  height: 480px;
}
</style>
