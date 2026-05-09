<template>
  <div class="flex-container">
    <div id="problem-main">
      <!--problem main-->
      <Panel :padding="40" shadow>
        <template #title>{{ problem.title }}</template>
        <div v-if="problemLoaded" id="problem-content" class="markdown-body" v-katex>
          <p class="title">{{ t('m.Description') }}</p>
          <p class="content" v-html="problem.description"></p>

          <p class="title">
            {{ t('m.Input') }}
            <span v-if="problem.io_mode.io_mode == 'File IO'">({{ t('m.FromFile') }}: {{ problem.io_mode.input }})</span>
          </p>
          <p class="content" v-html="problem.input_description"></p>

          <p class="title">
            {{ t('m.Output') }}
            <span v-if="problem.io_mode.io_mode == 'File IO'">({{ t('m.ToFile') }}: {{ problem.io_mode.output }})</span>
          </p>
          <p class="content" v-html="problem.output_description"></p>

          <div v-for="(sample, index) of problem.samples" :key="index">
            <div class="flex-container sample">
              <div class="sample-input">
                <p class="title">
                  {{ t('m.Sample_Input') }} {{ index + 1 }}
                  <a class="copy" @click="copyToClipboard(sample.input)">
                    <el-icon><DocumentCopy /></el-icon>
                  </a>
                </p>
                <pre>{{ sample.input }}</pre>
              </div>
              <div class="sample-output">
                <p class="title">{{ t('m.Sample_Output') }} {{ index + 1 }}</p>
                <pre>{{ sample.output }}</pre>
              </div>
            </div>
          </div>

          <div v-if="problem.hint">
            <p class="title">{{ t('m.Hint') }}</p>
            <el-card>
              <div class="content" v-html="problem.hint"></div>
            </el-card>
          </div>

          <div v-if="problem.source">
            <p class="title">{{ t('m.Source') }}</p>
            <p class="content">{{ problem.source }}</p>
          </div>
        </div>
      </Panel>
      <!--problem main end-->

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

        <el-row justify="space-between">
          <el-col :span="10">
            <div class="status" v-if="statusVisible">
              <template v-if="!contestID || (contestID && OIContestRealTimePermission)">
                <span>{{ t('m.Status') }}</span>
                <el-tag :type="submissionStatus.type" @click="handleRoute('/status/' + submissionId)" class="status-tag">
                  {{ t('m.' + submissionStatus.text.replace(/ /g, '_')) }}
                </el-tag>
              </template>
              <template v-else-if="contestID && !OIContestRealTimePermission">
                <el-alert type="success" show-icon :closable="false">{{ t('m.Submitted_successfully') }}</el-alert>
              </template>
            </div>
            <div v-else-if="problem.my_status === 0">
              <el-alert type="success" show-icon :closable="false">{{ t('m.You_have_solved_the_problem') }}</el-alert>
            </div>
            <div v-else-if="contestID && !OIContestRealTimePermission && submissionExists">
              <el-alert type="success" show-icon :closable="false">{{ t('m.You_have_submitted_a_solution') }}</el-alert>
            </div>
            <div v-if="contestEnded">
              <el-alert type="warning" show-icon :closable="false">{{ t('m.Contest_has_ended') }}</el-alert>
            </div>
          </el-col>

          <el-col :span="12">
            <template v-if="captchaRequired">
              <div class="captcha-container">
                <el-tooltip v-if="captchaRequired" content="Click to refresh" placement="top">
                  <img :src="captchaSrc" @click="getCaptchaSrc" />
                </el-tooltip>
                <el-input v-model="captchaCode" class="captcha-code" />
              </div>
            </template>
            <el-button type="warning" :loading="submitting" @click="submitCode"
                       :disabled="problemSubmitDisabled || submitted" class="fl-right">
              <span v-if="submitting">{{ t('m.Submitting') }}</span>
              <span v-else>{{ t('m.Submit') }}</span>
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
            {{ t('m.Problems') }}
          </VerticalMenuItem>
          <VerticalMenuItem :route="{ name: 'contest-announcement-list', params: { contestID } }">
            <el-icon><ChatDotRound /></el-icon>
            {{ t('m.Announcements') }}
          </VerticalMenuItem>
        </template>

        <VerticalMenuItem v-if="!contestID || OIContestRealTimePermission" :route="submissionRoute">
          <el-icon><List /></el-icon>
          {{ t('m.Submissions') }}
        </VerticalMenuItem>

        <template v-if="contestID">
          <VerticalMenuItem v-if="!contestID || OIContestRealTimePermission"
                            :route="{ name: 'contest-rank', params: { contestID } }">
            <el-icon><TrendCharts /></el-icon>
            {{ t('m.Rankings') }}
          </VerticalMenuItem>
          <VerticalMenuItem :route="{ name: 'contest-details', params: { contestID } }">
            <el-icon><House /></el-icon>
            {{ t('m.View_Contest') }}
          </VerticalMenuItem>
        </template>
      </VerticalMenu>

      <el-card id="info">
        <template #header>
          <div class="header">
            <el-icon><InfoFilled /></el-icon>
            <span class="card-title">{{ t('m.Information') }}</span>
          </div>
        </template>
        <ul>
          <li><p>ID</p><p>{{ problem._id }}</p></li>
          <li><p>{{ t('m.Time_Limit') }}</p><p>{{ problem.time_limit }}MS</p></li>
          <li><p>{{ t('m.Memory_Limit') }}</p><p>{{ problem.memory_limit }}MB</p></li>
          <li><p>{{ t('m.IOMode') }}</p><p>{{ problem.io_mode.io_mode }}</p></li>
          <li><p>{{ t('m.Created') }}</p><p>{{ problem.created_by.username }}</p></li>
          <li v-if="problem.difficulty"><p>{{ t('m.Level') }}</p><p>{{ t('m.' + problem.difficulty) }}</p></li>
          <li v-if="problem.total_score"><p>{{ t('m.Score') }}</p><p>{{ problem.total_score }}</p></li>
          <li>
            <p>{{ t('m.Tags') }}</p>
            <p>
              <el-popover trigger="hover" placement="left-end">
                <template #reference><a>{{ t('m.Show') }}</a></template>
                <el-tag v-for="tag in problem.tags" :key="tag" class="info-tag">{{ tag }}</el-tag>
              </el-popover>
            </p>
          </li>
        </ul>
      </el-card>

      <el-card id="pieChart" :body-style="{ padding: 0 }" v-if="!contestID || OIContestRealTimePermission">
        <template #header>
          <div class="chart-header">
            <el-icon><DataAnalysis /></el-icon>
            <span class="card-title">{{ t('m.Statistic') }}</span>
            <el-button size="small" id="detail" @click="graphVisible = !graphVisible">Details</el-button>
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
        <el-button @click="graphVisible = false">{{ t('m.Close') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  DocumentCopy, PictureFilled, ChatDotRound, List, TrendCharts, House,
  InfoFilled, DataAnalysis
} from '@element-plus/icons-vue'
import CodeMirror from '@oj/components/CodeMirror.vue'
import BlocklyEditor from '@oj/components/BlocklyEditor.vue'
import VerticalMenu from '@oj/components/verticalMenu/verticalMenu.vue'
import VerticalMenuItem from '@oj/components/verticalMenu/verticalMenu-item.vue'
import storage from '@/utils/storage'
import { useForm } from '@oj/components/mixins'
import { JUDGE_STATUS, CONTEST_STATUS, buildProblemCodeKey } from '@/utils/constants'
import api from '@oj/api'
import { pie as pieData, largePie as largePieData } from './chartData'
import { useContestStore } from '@/store/contest'
import { useAppStore } from '@/store/app'

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

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const contestStore = useContestStore()
const appStore = useAppStore()
const { captchaSrc, getCaptchaSrc } = useForm()

const statusVisible = ref(false)
const captchaRequired = ref(false)
const graphVisible = ref(false)
const submissionExists = ref(false)
const captchaCode = ref('')
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
  template: {},
  languages: [],
  created_by: { username: '' },
  tags: [],
  io_mode: { io_mode: 'Standard IO' }
})
const pie = ref(structuredCloneWithFunctions(pieData))
const largePie = ref(structuredCloneWithFunctions(largePieData))

let refreshStatus = null

const OIContestRealTimePermission = computed(() => contestStore.OIContestRealTimePermission)
const problemSubmitDisabled = computed(() => contestStore.problemSubmitDisabled)
const contestRuleType = computed(() => contestStore.contestRuleType)
const contestStatusVal = computed(() => contestStore.contestStatus)

const contestEnded = computed(() => contestStatusVal.value === CONTEST_STATUS.ENDED)

const submissionStatus = computed(() => ({
  text: JUDGE_STATUS[result.value.result]['name'],
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
    ElMessage.success('Code copied')
  }).catch(() => {
    ElMessage.error('Failed to copy code')
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
    api.submissionExists(prob.id).then(r => {
      submissionExists.value = r.data.data
    })
    prob.languages = prob.languages.sort()
    problemLoaded.value = false
    problem.value = prob
    if (prob.statistic_info) changePie(prob)
    problemLoaded.value = true

    // Load from storage
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
  ElMessageBox.confirm(t('m.Are_you_sure_you_want_to_reset_your_code'), 'Confirm').then(() => {
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

function submitCode () {
  if (code.value.trim() === '') {
    ElMessage.error(t('m.Code_can_not_be_empty'))
    return
  }
  submissionId.value = ''
  result.value = { result: 9 }
  submitting.value = true

  const data = {
    problem_id: problem.value.id,
    language: language.value,
    code: code.value,
    contest_id: contestID.value,
    blockly_state: language.value === 'Block Coding' ? blocklyWorkspace.value : ''
  }
  if (captchaRequired.value) {
    data.captcha = captchaCode.value
  }

  const submitFunc = (d, detailsVisible) => {
    statusVisible.value = true
    api.submitCode(d).then(res => {
      submissionId.value = res.data.data && res.data.data.submission_id
      submitting.value = false
      submissionExists.value = true
      if (!detailsVisible) {
        ElMessageBox.alert(t('m.Submit_code_successfully'), t('m.Success'))
        return
      }
      submitted.value = true
      checkSubmissionStatus()
    }, res => {
      getCaptchaSrc()
      if (res.data?.data?.startsWith('Captcha is required')) {
        captchaRequired.value = true
      }
      submitting.value = false
      statusVisible.value = false
    })
  }

  if (contestRuleType.value === 'OI' && !OIContestRealTimePermission.value) {
    if (submissionExists.value) {
      ElMessageBox.confirm(t('m.You_have_submission_in_this_problem_sure_to_cover_it'), '').then(() => {
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
  storage.set(buildProblemCodeKey(problem.value._id, from.params.contestID), {
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
.card-title {
  margin-left: 8px;
}

.flex-container {
  #problem-main {
    flex: auto;
    margin-right: 18px;
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
  .captcha-container {
    display: inline-block;
    .captcha-code {
      width: auto;
      margin-top: -20px;
      margin-left: 20px;
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
