<template>
  <div class="problem">
    <Panel :title="title">
      <el-form ref="formRef" :model="problem" :rules="rules" label-position="top" label-width="70px">
        <el-row :gutter="20">
          <!-- 문제 번호는 서버가 정한다. 공개 문제는 pk, 대회 문제는 담은 순서다. -->
          <el-col :span="24">
            <el-form-item prop="title" label="제목" required>
              <el-input placeholder="제목" v-model="problem.title" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="24">
            <el-form-item prop="description" label="설명" required>
              <MarkdownEditor v-model="problem.description" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="24">
            <el-form-item prop="input_description" label="입력 설명">
              <MarkdownEditor v-model="problem.input_description" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item prop="output_description" label="출력 설명">
              <MarkdownEditor v-model="problem.output_description" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="시간 제한 (ms)" required>
              <el-input type="number" placeholder="시간 제한" v-model="problem.time_limit" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="메모리 제한 (MB)" required>
              <el-input type="number" placeholder="메모리 제한" v-model="problem.memory_limit" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="난이도">
              <el-select class="difficulty-select" size="small" placeholder="난이도" v-model="problem.difficulty">
                <el-option v-for="d in DIFFICULTY" :key="d.value" :label="d.label" :value="d.value" />
              </el-select>
              <!-- 기준이 없으면 출제자마다 단계가 흔들린다. 고르는 자리에서 바로 보이게 둔다. -->
              <el-popover placement="right" :width="300" trigger="hover">
                <template #reference>
                  <el-icon class="difficulty-help"><QuestionFilled /></el-icon>
                </template>
                <p class="guide-title">난이도 기준</p>
                <ul class="guide-list">
                  <li v-for="d in DIFFICULTY" :key="d.value">
                    <b :style="{ color: d.color }">{{ d.label }}</b> {{ DIFFICULTY_GUIDE[d.value] }}
                  </li>
                </ul>
              </el-popover>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="4">
            <el-form-item label="공개">
              <el-switch v-model="problem.visible" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="태그" :error="error.tags" required>
              <el-select v-model="problem.tags" multiple filterable remote reserve-keyword
                         class="tag-select" placeholder="태그"
                         :remote-method="querySearch" :loading="tagLoading">
                <el-option v-for="tag in tagOptions" :key="tag.name" :label="formatTagLabel(tag)" :value="tag.name" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="언어" :error="error.languages" required>
              <el-checkbox-group v-model="problem.languages">
                <el-tooltip v-for="lang in allLanguage.languages" :key="'lang' + lang.name"
                            class="spj-radio" effect="dark" :content="lang.description" placement="top-start">
                  <el-checkbox :label="lang.name" />
                </el-tooltip>
              </el-checkbox-group>
            </el-form-item>
          </el-col>
        </el-row>

        <div>
          <el-form-item v-for="(sample, index) in problem.samples" :key="'sample' + index">
            <Accordion :title="'Sample ' + (index + 1)">
              <template #header>
                <el-button type="warning" size="small" :icon="Delete" @click="deleteSample(index)">삭제</el-button>
              </template>
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="입력 예제" required>
                    <el-input :rows="5" type="textarea" placeholder="입력 예제" v-model="sample.input" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="출력 예제" required>
                    <el-input :rows="5" type="textarea" placeholder="출력 예제" v-model="sample.output" />
                  </el-form-item>
                </el-col>
              </el-row>
              <!-- 손으로 치면 실제 채점 데이터와 어긋날 수 있다. 케이스에서
                   가져오면 그럴 수 없고, 가져온 뒤 고치는 것은 자유다. -->
              <el-form-item label="테스트 케이스에서 가져오기">
                <el-select :model-value="null" placeholder="케이스" class="pick-case"
                           :disabled="!pickableCases.length"
                           @change="fillSample(sample, $event)">
                  <el-option v-for="c in pickableCases" :key="c.index" :value="c.index"
                             :label="`${c.index}번`" :disabled="c.too_large" />
                </el-select>
                <span v-if="!pickableCases.length" class="pick-hint">
                  케이스를 넣으면 여기서 가져올 수 있습니다
                </span>
              </el-form-item>
            </Accordion>
          </el-form-item>
        </div>
        <div class="add-sample-btn">
          <button type="button" class="add-samples" @click="addSample">
            <el-icon class="add-icon"><Plus /></el-icon>예제 추가
          </button>
        </div>

        <el-form-item class="hint-item" label="힌트">
          <MarkdownEditor v-model="problem.hint" placeholder="" />
        </el-form-item>

        <el-form-item label="코드 템플릿">
          <el-row class="full-width">
            <el-col :span="24" v-for="(v, k) in template" :key="'template' + k">
              <el-checkbox v-model="v.checked">{{ k }}</el-checkbox>
              <div v-if="v.checked" class="full-width">
                <code-mirror v-model="v.code" :mode="v.mode" />
              </div>
            </el-col>
          </el-row>
        </el-form-item>

        <el-form-item label="스페셜 저지" :error="error.spj">
          <el-col :span="24">
            <el-checkbox :model-value="problem.spj" @click.prevent="switchSpj">Special Judge 사용</el-checkbox>
          </el-col>
        </el-form-item>
        <el-form-item v-if="problem.spj">
          <Accordion title="Special Judge 코드">
            <template #header>
              <span>SPJ 언어</span>
              <el-radio-group v-model="problem.spj_language">
                <el-tooltip v-for="lang in allLanguage.spj_languages" :key="lang.name"
                            class="spj-radio" effect="dark" :content="lang.description" placement="top-start">
                  <el-radio :label="lang.name">{{ lang.name }}</el-radio>
                </el-tooltip>
              </el-radio-group>
              <el-button type="primary" size="small" @click="compileSPJ" :loading="loadingCompile">
                컴파일
              </el-button>
            </template>
            <code-mirror v-model="problem.spj_code" :mode="spjMode" />
          </Accordion>
        </el-form-item>

        <el-row :gutter="20">
          <el-col :span="4">
            <el-form-item label="유형">
              <el-radio-group v-model="problem.rule_type">
                <el-radio label="ACM">ACM</el-radio>
                <el-radio label="OI">OI</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="10">
            <el-form-item label="테스트 케이스" :error="error.testCase">
              <el-upload action="/api/admin/test_case" name="file" :data="{ spj: problem.spj }"
                         :show-file-list="false"
                         :on-success="uploadSucceeded" :on-error="uploadFailed">
                <el-button size="small">zip 파일로 채우기</el-button>
              </el-upload>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="IO 모드">
              <!-- 파일 입출력은 쓰지 않아 선택지에서 감춘다. 모델·채점기 쪽은 그대로라
                   필요해지면 아래 한 줄만 되살리면 된다.
              <el-radio label="File IO">파일 입출력</el-radio> -->
              <el-radio-group v-model="problem.io_mode.io_mode">
                <el-radio label="Standard IO">표준 입출력</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="4" v-if="problem.io_mode.io_mode === 'File IO'">
            <el-form-item label="입력 파일명" required>
              <el-input v-model="problem.io_mode.input" />
            </el-form-item>
          </el-col>
          <el-col :span="4" v-if="problem.io_mode.io_mode === 'File IO'">
            <el-form-item label="출력 파일명" required>
              <el-input v-model="problem.io_mode.output" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <p class="case-guide">
              입력과 출력의 짝을 적습니다. 줄을 펼쳐서 고칠 수 있고, 직접 쳐 넣는 것은
              {{ MAX_CASES }}개까지입니다(zip 으로 채운 것은 세지 않습니다).
              너무 큰 케이스는 여기서 고칠 수 없고 그대로 유지됩니다.
              <template v-if="problem.spj">
                스페셜 저지는 판정 코드가 맞고 틀림을 정하므로 출력을 넣지 않습니다.
              </template>
            </p>
            <el-table :data="cases" class="full-width" size="small" row-key="key">
              <el-table-column type="expand">
                <template #default="{ row }">
                  <div v-if="row.too_large" class="case-locked">
                    내용이 커서 여기서 고칠 수 없습니다. 저장해도 그대로 유지됩니다.
                  </div>
                  <!-- el-row 의 gutter 는 음수 마진이라 표의 펼침 칸을 넘어간다 -->
                  <div v-else class="case-editor">
                    <el-input v-model="row.input" type="textarea" :rows="5" placeholder="입력" />
                    <el-input v-if="!problem.spj" v-model="row.output" type="textarea" :rows="5"
                              placeholder="출력" />
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="#" width="60" align="center">
                <template #default="{ $index }">{{ $index + 1 }}</template>
              </el-table-column>
              <el-table-column label="입력">
                <template #default="{ row }"><span class="case-peek">{{ peek(row, 'input') }}</span></template>
              </el-table-column>
              <el-table-column v-if="!problem.spj" label="출력">
                <template #default="{ row }"><span class="case-peek">{{ peek(row, 'output') }}</span></template>
              </el-table-column>
              <el-table-column label="점수" width="120">
                <template #default="{ row }">
                  <el-input size="small" v-model="row.score" placeholder="점수"
                            :disabled="problem.rule_type !== 'OI'" />
                </template>
              </el-table-column>
              <el-table-column width="80" align="center">
                <template #default="{ $index }">
                  <el-button size="small" type="danger" link :disabled="cases.length === 1"
                             @click="cases.splice($index, 1)">삭제</el-button>
                </template>
              </el-table-column>
              <template #empty>
                <span>케이스가 없습니다. "케이스 추가" 나 "zip 파일로 채우기" 를 쓰세요.</span>
              </template>
            </el-table>
            <el-button size="small" :icon="Plus" class="add-case"
                       @click="cases.push(newCase())">케이스 추가</el-button>
          </el-col>
        </el-row>

        <el-form-item label="정답 코드 (선택)">
          <!-- 내용칸이 flex + wrap 이라 그냥 두면 셀렉트와 편집기가 한 줄에 선다.
               편집기는 그 남은 폭으로 초기화되어 좁게 굳는다.
               이 파일의 다른 편집기들처럼 한 줄씩 감싼다. -->
          <el-col :span="24">
            <el-select v-model="problem.solver_language" placeholder="언어" clearable
                       class="solver-language">
              <el-option v-for="lang in allLanguage.languages" :key="lang.name"
                         :value="lang.name" :label="lang.name" />
            </el-select>
          </el-col>
          <el-col :span="24">
            <code-mirror v-model="problem.solver_code" :mode="solverMode" />
          </el-col>
          <div class="verify-row form-item-row">
            <el-button size="small" :loading="verifying" :disabled="!problem.solver_code"
                       @click="verify">테스트 케이스 확인</el-button>
            <span v-if="verifyMessage" :class="['verify-message', { bad: verifyFailed }]">
              {{ verifyMessage }}
            </span>
          </div>
          <p class="case-guide form-item-row">
            넣어 둔 출력과 정답 코드의 결과가 같은지 봅니다. 저장과는 따로 돌고,
            통과하지 못해도 저장할 수 있습니다.
          </p>
        </el-form-item>

        <el-form-item label="출처">
          <el-input placeholder="출처" v-model="problem.source" />
        </el-form-item>
        <save @click="submit">저장</save>
      </el-form>
    </Panel>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, QuestionFilled } from '@element-plus/icons-vue'
import MarkdownEditor from '../../components/MarkdownEditor.vue'
import Accordion from '../../components/Accordion.vue'
import CodeMirror from '../../components/CodeMirror.vue'
import api from '../../api.js'
import { DIFFICULTY, DIFFICULTY_GUIDE } from '@/utils/constants'
const route = useRoute()
const router = useRouter()

const formRef = ref(null)
// 입력·출력 설명은 비워둘 수 있다(problem/serializers.py 참고).
// 입력이 없는 문제도 있고, 교사가 비워 만든 문제를 관리자가 열었을 때
// 아무것도 고치지 않았는데 저장이 막히면 안 된다.
const rules = {
  title: { required: true, message: '제목을 입력하세요', trigger: 'blur' },
  description: { required: true, message: '설명을 입력하세요', trigger: 'blur' }
}

const loadingCompile = ref(false)
const tagLoading = ref(false)
const mode = ref('')
const testCaseUploaded = ref(false)
const allLanguage = ref({})
const tagOptions = ref([])
const template = ref({})
const title = ref('')
const spjMode = ref('')
const routeName = ref('')
const error = reactive({ tags: '', spj: '', languages: '', testCase: '' })

function defaultProblem () {
  return {
    title: '', description: '', input_description: '', output_description: '',
    time_limit: 1000, memory_limit: 256, difficulty: 'L1', visible: true,
    tags: [], languages: [], template: {}, samples: [{ input: '', output: '' }],
    spj: false, spj_language: '', spj_code: '', spj_compile_ok: false,
    solver_language: '', solver_code: '',
    test_case_id: '', test_case_score: [], rule_type: 'ACM', hint: '', source: '',
    io_mode: { io_mode: 'Standard IO', input: 'input.txt', output: 'output.txt' }
  }
}

const problem = ref(defaultProblem())
const MAX_CASES = 20
const MAX_SAMPLE_BYTES = 2 * 1024
// newCase() 가 이 값을 쓴다. 선언 순서를 지켜야 TDZ 에 걸리지 않는다.
let caseKey = 0
const cases = ref([])
const verifying = ref(false)
const verifyMessage = ref('')
const verifyFailed = ref(false)
const verificationToken = ref('')
const solverMode = ref('text/x-csrc')
let verifyTimer = null

function verify () {
  const payload = {
    ...casePayload(),
    // keep 으로 보낸 케이스를 서버가 이 문제의 것에서 찾아 쓴다
    problem_id: problem.value.id,
    solver_language: problem.value.solver_language,
    solver_code: problem.value.solver_code,
    spj: problem.value.spj,
    spj_language: problem.value.spj_language,
    spj_code: problem.value.spj_code,
    time_limit: problem.value.time_limit,
    memory_limit: problem.value.memory_limit,
    io_mode: problem.value.io_mode
  }
  if (!payload.cases?.length && !payload.test_case_id) {
    ElMessage.error('테스트 케이스를 먼저 넣어주세요')
    return
  }
  verifying.value = true
  verifyFailed.value = false
  verifyMessage.value = '확인하는 중입니다…'
  api.verifySolution(payload).then(res => {
    verificationToken.value = res.data.data.token
    pollVerification()
  }, () => {
    verifying.value = false
    verifyMessage.value = ''
  })
}

// 채점 서버가 바쁘면 자리가 날 때까지 기다리므로 결과가 늦을 수 있다
// 화면을 떠나면 검증 결과는 필요 없다. 캐시에 남은 것은 시간이 지나 사라진다.
onBeforeUnmount(() => clearTimeout(verifyTimer))

function pollVerification () {
  verifyTimer = setTimeout(() => {
    api.getVerification(verificationToken.value).then(res => {
      const record = res.data.data
      if (record.status !== 'done') {
        pollVerification()
        return
      }
      verifying.value = false
      verifyFailed.value = !record.passed
      verifyMessage.value = record.message
    }, () => {
      verifying.value = false
      verifyMessage.value = '확인하지 못했습니다. 다시 눌러주세요'
    })
  }, 2000)
}

// 예제는 여기서 골라 채운다. 표에 있는 케이스가 곧 후보다.
const pickableCases = computed(() => cases.value.map((c, index) => ({
  index: index + 1,
  input: c.input,
  // 스페셜 저지는 출력 칸이 없다. null 이면 예제 출력을 건드리지 않는다.
  output: problem.value.spj ? null : c.output,
  // 예제는 문제 화면에 그대로 나가므로 큰 것은 고를 수 없다
  too_large: c.too_large || byteLength(c.input) > MAX_SAMPLE_BYTES ||
    byteLength(c.output) > MAX_SAMPLE_BYTES
})))

// 직접 쳐 넣은 것만 센다. zip 으로 채우거나 불러온 것은 상한에 걸리지 않는다.
const typedCount = computed(() => cases.value.filter(isTyped).length)

function byteLength (text) {
  return new TextEncoder().encode(text || '').length
}

function isTyped (row) {
  if (row.too_large) return false
  if (!row.loaded) return true
  return row.input !== row.loaded.input || row.output !== row.loaded.output
}

function newCase () {
  return { key: ++caseKey, index: null, input: '', output: '', too_large: false,
    input_size: 0, output_size: 0, score: 0, loaded: null }
}

// 표에는 한 줄만 보여준다. 펼치면 전부 고칠 수 있다.
function peek (row, field) {
  if (row.too_large) return `${row[field + '_size']}바이트 (여기서 고칠 수 없음)`
  const text = (row[field] || '').trim()
  if (!text) return '(비어 있음)'
  const first = text.split('\n')[0]
  return first.length > 40 ? first.slice(0, 40) + '…' : first
}

// 서버가 준 케이스로 표를 채운다. loaded 를 남겨 두어 "고쳤나" 를 알 수 있다.
function fillCases (loaded, scores = []) {
  cases.value = loaded.map((c, index) => ({
    key: ++caseKey,
    index: c.index,
    input: c.input || '',
    output: c.output || '',
    too_large: c.too_large,
    input_size: c.input_size,
    output_size: c.output_size,
    score: scores[index]?.score ?? Math.floor(100 / (loaded.length || 1)),
    loaded: c.too_large ? null : { input: c.input || '', output: c.output || '' }
  }))
  if (!cases.value.length) cases.value = [newCase()]
}

// 못 고치는 것과 손대지 않은 것은 번호만 보낸다 - 서버가 이전 파일을 그대로 쓴다
function casePayload () {
  return {
    cases: cases.value
      .filter(c => c.too_large || c.loaded || c.input.trim() || c.output.trim())
      .map(c => (isTyped(c) ? { input: c.input, output: c.output } : { keep: c.index }))
  }
}

// 케이스 내용을 예제 칸에 복사한다. 그 뒤 고치는 것은 사용자 몫이다.
function fillSample (sample, index) {
  const picked = pickableCases.value.find(c => c.index === index)
  if (!picked) return
  sample.input = picked.input || ''
  if (picked.output !== null && picked.output !== undefined) sample.output = picked.output
}

onMounted(() => {
  getTagOptions()
  routeName.value = route.name
  mode.value = routeName.value === 'edit-problem' ? 'edit' : 'add'

  api.getLanguages().then(res => {
    problem.value = defaultProblem()

    problem.value.spj_language = 'C'
    allLanguage.value = res.data.data

    if (mode.value === 'edit') {
      title.value = '문제 수정'
      const funcName = 'getProblem'
      api[funcName](route.params.problemId).then(problemRes => {
        const data = problemRes.data.data
        if (!data.spj_code) data.spj_code = ''
        data.spj_language = data.spj_language || 'C'
        data.solver_code = data.solver_code || ''
        data.solver_language = data.solver_language || ''
        problem.value = data
        testCaseUploaded.value = true
        api.getTestCasePreview(data.id).then(
          preview => fillCases(preview.data.data.cases, data.test_case_score), () => {})
        // 지난 검증 결과를 되살린다. 케이스가 바뀌면 서버가 지워 두므로 없을 수 있다.
        if (data.solver_verified_at) {
          verifyFailed.value = !data.solver_passed
          verifyMessage.value = data.solver_message
        }
      })
    } else {
      title.value = '문제 추가'
      cases.value = [newCase()]
      for (const item of res.data.data.languages) {
        problem.value.languages.push(item.name)
      }
    }
  })
})

watch(() => route.fullPath, () => {
  formRef.value?.resetFields()
  problem.value = defaultProblem()
})

watch(() => problem.value.languages, (newVal) => {
  const data = {}
  const languages = JSON.parse(JSON.stringify(newVal)).sort()
  for (const item of languages) {
    if (template.value[item] === undefined) {
      const langConfig = allLanguage.value.languages?.find(lang => lang.name === item)
      if (!langConfig) continue
      if (problem.value.template[item] === undefined) {
        data[item] = { checked: false, code: langConfig.config.template, mode: langConfig.content_type }
      } else {
        data[item] = { checked: true, code: problem.value.template[item], mode: langConfig.content_type }
      }
    } else {
      data[item] = template.value[item]
    }
  }
  template.value = data
})

watch(() => problem.value.spj_language, () => {
  const lang = allLanguage.value.spj_languages?.find(item => item.name === problem.value.spj_language)
  if (lang) spjMode.value = lang.content_type
})

function switchSpj () {
  if (testCaseUploaded.value) {
    ElMessageBox.confirm('채점 방식을 바꾸면 테스트 케이스를 다시 업로드해야 합니다', '경고', {
      confirmButtonText: 'Yes', cancelButtonText: '취소', type: 'warning'
    }).then(() => {
      problem.value.spj = !problem.value.spj
      resetTestCase()
    }).catch(() => {})
  } else {
    problem.value.spj = !problem.value.spj
  }
}

function getTagOptions (keyword = '') {
  tagLoading.value = true
  api.getAdminProblemTagList({ keyword }).then(res => {
    const options = res.data.data || []
    const optionNames = new Set(options.map(tag => tag.name))
    const selectedOptions = problem.value.tags
      .filter(tag => !optionNames.has(tag))
      .map(tag => ({ name: tag }))
    tagOptions.value = selectedOptions.concat(options)
    tagLoading.value = false
  }, () => {
    tagLoading.value = false
  })
}

function querySearch (queryString) {
  getTagOptions(queryString)
}

function formatTagLabel (tag) {
  return tag.aliases?.length ? `${tag.name} (${tag.aliases.join(', ')})` : tag.name
}

function resetTestCase () {
  testCaseUploaded.value = false
  problem.value.test_case_score = []
  problem.value.test_case_id = ''
}

function addSample () { problem.value.samples.push({ input: '', output: '' }) }
function deleteSample (index) { problem.value.samples.splice(index, 1) }

function uploadSucceeded (response) {
  if (response.error) { ElMessage.error(response.data); return }
  const fileList = response.data.info
  for (const file of fileList) {
    file.score = (100 / fileList.length).toFixed(0)
    if (!file.output_name && problem.value.spj) file.output_name = '-'
  }
  problem.value.test_case_score = fileList
  testCaseUploaded.value = true
  problem.value.test_case_id = response.data.id
  // 올린 케이스로 표를 채운다. 여기서 바로 고칠 수 있다.
  fillCases(response.data.cases || [], fileList)
  ElMessage.success(`케이스 ${fileList.length}개를 채웠습니다`)
}

function uploadFailed () { ElMessage.error('업로드에 실패했습니다') }

function compileSPJ () {
  loadingCompile.value = true
  api.compileSPJ({
    id: problem.value.id, spj_code: problem.value.spj_code, spj_language: problem.value.spj_language
  }).then(() => {
    loadingCompile.value = false
    problem.value.spj_compile_ok = true
    error.spj = ''
  }, (err) => {
    loadingCompile.value = false
    problem.value.spj_compile_ok = false
    ElMessageBox.alert(err.data?.data || '컴파일 오류', '컴파일 에러', { type: 'error', customClass: 'dialog-compile-error' })
  })
}

async function submit () {
  // 규칙을 정의해 두고도 검사하지 않아, 비어 있는 항목이 서버의 영문 에러
  // ("This field may not be blank")로만 드러나고 어느 칸인지 알 수 없었다.
  const valid = await formRef.value.validate().then(() => true, () => false)
  if (!valid) { ElMessage.error('비어 있는 필수 항목이 있습니다'); return }
  if (!problem.value.samples.length) { ElMessage.error('예제를 입력하세요'); return }
  for (const sample of problem.value.samples) {
    if (!sample.input || !sample.output) { ElMessage.error('예제 입력과 출력을 모두 입력하세요'); return }
  }
  if (!problem.value.tags.length) { error.tags = 'Please add at least one tag'; ElMessage.error(error.tags); return }
  if (problem.value.spj) {
    if (!problem.value.spj_code) { error.spj = 'Spj code is required' }
    else if (!problem.value.spj_compile_ok) { error.spj = 'SPJ code has not been successfully compiled' }
    if (error.spj) { ElMessage.error(error.spj); return }
  }
  if (!problem.value.languages.length) { error.languages = 'Please choose at least one language for problem'; ElMessage.error(error.languages); return }
  const payloadCases = casePayload().cases
  if (!payloadCases.length) { error.testCase = '테스트 케이스를 넣어주세요'; ElMessage.error(error.testCase); return }
  if (typedCount.value > MAX_CASES) {
    ElMessage.error(`직접 쳐 넣는 테스트 케이스는 ${MAX_CASES}개까지입니다`); return
  }
  if (problem.value.rule_type === 'OI') {
    for (const row of cases.value) {
      if (parseInt(row.score) <= 0 || isNaN(parseInt(row.score))) {
        ElMessage.error('테스트 케이스 점수가 올바르지 않습니다'); return
      }
    }
  }

  problem.value.languages = problem.value.languages.sort()
  problem.value.template = {}
  for (const k in template.value) {
    if (template.value[k].checked) problem.value.template[k] = template.value[k].code
  }

  const payload = { ...problem.value }
  // 검증해 둔 것이 있으면 표를 함께 보낸다. 그사이 케이스를 고쳤으면 서버가
  // 지문을 대조해 붙이지 않는다.
  if (verificationToken.value) payload.verification_token = verificationToken.value
  // 케이스는 늘 전부 보낸다. 고치지 않은 것은 번호만 가고, 내용이 예전과 같으면
  // 서버가 파일을 갈아끼우지 않으므로 재채점도 돌지 않는다.
  payload.cases = payloadCases
  payload.test_case_id = ''
  payload.test_case_score = cases.value.map((row, index) => ({
    input_name: `${index + 1}.in`, output_name: problem.value.spj ? '' : `${index + 1}.out`,
    score: parseInt(row.score) || 0
  }))

  const funcName = routeName.value === 'create-problem' ? 'createProblem' : 'editProblem'
  api[funcName](payload).then(res => {
    // 테스트케이스를 갈아끼우면 서버가 이 문제의 제출을 전부 다시 채점한다.
    // 정답률과 대회 순위가 잠시 뒤 바뀌므로 알려준다.
    if (res.data.data?.rejudging) {
      ElMessage.warning('테스트 케이스가 바뀌어 이 문제의 제출을 다시 채점합니다. ' +
        '정답률과 대회 순위는 채점이 끝난 뒤 반영됩니다.')
    }
    router.push({ name: 'problem-list' })
  }).catch(() => {})
}
</script>

<style lang="less" scoped>
.verify-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 8px;
}

.verify-message {
  font-size: 13px;
  color: #67c23a;
  white-space: pre-line;
}

.verify-message.bad {
  color: #e6a23c;
}

.solver-language {
  width: 160px;
  margin-bottom: 8px;
}

.case-editor {
  display: flex;
  gap: 12px;
  padding: 4px 0;
}

/* 기본값 auto 면 안의 글이 길 때 칸이 줄지 않아 표가 가로로 넘친다 */
.case-editor > * {
  flex: 1;
  min-width: 0;
}

.case-locked {
  font-size: 12px;
  color: #909399;
  padding: 8px 0;
}

.case-peek {
  font-family: Consolas, Monaco, "Courier New", monospace;
  font-size: 12px;
  color: #606266;
  white-space: pre;
}

.case-guide {
  font-size: 12px;
  color: #909399;
  line-height: 1.8;
  margin: 0 0 8px;
}

.add-case {
  margin-top: 8px;
}

.pick-case {
  width: 160px;
}

.pick-hint {
  margin-left: 10px;
  font-size: 12px;
  color: #909399;
}

.problem {
  .difficulty-help {
    margin-left: 6px;
    color: #909399;
    cursor: help;
    vertical-align: middle;
  }

  .guide-title {
    font-weight: 600;
    margin-bottom: 6px;
  }

  .guide-list {
    margin: 0 0 0 4px;
    padding-left: 12px;
    line-height: 1.9;
    font-size: 13px;
  }

  .difficulty-select { width: 120px; }
  .spj-radio {
    margin-left: 10px;
    &:last-child { margin-right: 20px; }
  }
  .tag-select { width: 100%; }
  .accordion { margin-bottom: 10px; width: 100%; }
  .add-samples {
    width: 100%; background-color: #fff; border: 1px dashed #aaa;
    outline: none; cursor: pointer; color: #666; height: 35px; font-size: 14px;
    &:hover { background-color: #f9fafc; }
  }
  .add-sample-btn { margin-bottom: 10px; }
  .add-icon { margin-right: 10px; }
  .hint-item { margin-top: 20px; }
  .full-width { width: 100%; }
  :deep(.cm-editor) {
    border: 1px solid #dcdfe6;
    border-radius: 4px;
  }
}
</style>

<style>
.dialog-compile-error { width: auto; max-width: 80%; overflow-x: scroll; }
</style>
