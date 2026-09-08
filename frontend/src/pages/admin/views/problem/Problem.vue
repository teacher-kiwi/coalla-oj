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
                <el-button v-if="canLoadSaved" size="small" class="pick-hint"
                           :loading="loadingCases" @click="loadSavedCases">
                  저장된 케이스 불러오기
                </el-button>
                <span v-else-if="!pickableCases.length" class="pick-hint">
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
              <el-radio-group v-model="caseSource" size="small" class="case-source">
                <el-radio-button value="file">파일 올리기</el-radio-button>
                <el-radio-button value="manual">직접 입력</el-radio-button>
              </el-radio-group>
              <el-upload v-if="caseSource === 'file'"
                         action="/api/admin/test_case" name="file" :data="{ spj: problem.spj }"
                         :show-file-list="true" :on-success="uploadSucceeded" :on-error="uploadFailed">
                <el-button size="small" type="primary">파일 선택</el-button>
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
          <el-col :span="24" v-if="caseSource === 'manual'">
            <p class="case-guide">
              입력과 출력의 짝을 적습니다. 배점은 고르게 나뉩니다 - 케이스마다 다른
              점수를 주려면 파일로 올린 뒤 아래 표에서 고치세요.
              <template v-if="problem.spj">
                스페셜 저지는 판정 코드가 맞고 틀림을 정하므로 출력을 넣지 않습니다.
              </template>
            </p>
            <el-table :data="cases" class="full-width" size="small">
              <el-table-column label="#" width="50" align="center">
                <template #default="{ $index }">{{ $index + 1 }}</template>
              </el-table-column>
              <el-table-column label="입력">
                <template #default="{ row }">
                  <el-input v-model="row.input" type="textarea" :rows="3" placeholder="입력" />
                </template>
              </el-table-column>
              <el-table-column v-if="!problem.spj" label="출력">
                <template #default="{ row }">
                  <el-input v-model="row.output" type="textarea" :rows="3" placeholder="출력" />
                </template>
              </el-table-column>
              <el-table-column width="120" align="center">
                <template #default="{ $index }">
                  <el-button size="small" type="danger" link :disabled="cases.length === 1"
                             @click="cases.splice($index, 1)">삭제</el-button>
                </template>
              </el-table-column>
            </el-table>
            <el-button size="small" :icon="Plus" class="add-case"
                       @click="cases.push({ input: '', output: '' })">케이스 추가</el-button>
          </el-col>
          <el-col :span="24" v-else>
            <el-table :data="problem.test_case_score" class="full-width">
              <el-table-column prop="input_name" label="입력" />
              <el-table-column prop="output_name" label="출력" />
              <el-table-column prop="score" label="점수">
                <template #default="{ row }">
                  <el-input size="small" placeholder="점수" v-model="row.score"
                            :disabled="problem.rule_type !== 'OI'" />
                </template>
              </el-table-column>
            </el-table>
          </el-col>
        </el-row>

        <el-form-item label="출처">
          <el-input placeholder="출처" v-model="problem.source" />
        </el-form-item>
        <save @click="submit">저장</save>
      </el-form>
    </Panel>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
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
    test_case_id: '', test_case_score: [], rule_type: 'ACM', hint: '', source: '',
    io_mode: { io_mode: 'Standard IO', input: 'input.txt', output: 'output.txt' }
  }
}

const problem = ref(defaultProblem())
// 테스트 케이스를 넣는 두 가지 길. 섞을 수 없어 하나를 고른다.
const caseSource = ref('file')
const cases = ref([{ input: '', output: '' }])
// 업로드가 돌려주는 케이스 내용. 여기서 예제를 가져온다.
const uploadedCases = ref([])
const SAMPLE_PICK_LIMIT = 5
const loadingCases = ref(false)

// 고칠 때 이미 저장된 케이스에서 예제를 다시 고를 수 있게 한다
const canLoadSaved = computed(() =>
  caseSource.value === 'file' && !uploadedCases.value.length && !!problem.value.id)

function loadSavedCases () {
  loadingCases.value = true
  api.getTestCasePreview(problem.value.id).then(res => {
    loadingCases.value = false
    uploadedCases.value = res.data.data.cases
  }, () => {
    loadingCases.value = false
  })
}

const pickableCases = computed(() => {
  if (caseSource.value === 'file') return uploadedCases.value
  return cases.value.slice(0, SAMPLE_PICK_LIMIT).map((c, index) => ({
    // 스페셜 저지는 출력 칸이 없다. null 이면 예제 출력을 건드리지 않는다.
    index: index + 1, input: c.input, output: problem.value.spj ? null : c.output,
    too_large: false
  }))
})

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
        problem.value = data
        testCaseUploaded.value = true
      })
    } else {
      title.value = '문제 추가'
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
  uploadedCases.value = response.data.cases || []
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
  const filledCases = cases.value.filter(c => c.input.trim() || c.output.trim())
  if (caseSource.value === 'manual') {
    if (!filledCases.length) { error.testCase = '테스트 케이스를 넣어주세요'; ElMessage.error(error.testCase); return }
  } else if (!testCaseUploaded.value) {
    error.testCase = '테스트 케이스 파일을 올려주세요'; ElMessage.error(error.testCase); return
  } else if (problem.value.rule_type === 'OI') {
    // 배점 표는 파일로 올렸을 때만 있다. 직접 입력은 서버가 고르게 나눈다.
    for (const item of problem.value.test_case_score) {
      if (parseInt(item.score) <= 0 || isNaN(parseInt(item.score))) {
        ElMessage.error('테스트 케이스 점수가 올바르지 않습니다'); return
      }
    }
  }

  problem.value.languages = problem.value.languages.sort()
  problem.value.template = {}
  for (const k in template.value) {
    if (template.value[k].checked) problem.value.template[k] = template.value[k].code
  }

  // 두 길 중 하나만 보낸다. 서버가 둘 다 오면 거절한다.
  const payload = { ...problem.value }
  if (caseSource.value === 'manual') {
    payload.cases = filledCases.map(c => ({ input: c.input, output: c.output }))
    payload.test_case_id = ''
    payload.test_case_score = []
  }

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
.case-source {
  margin-bottom: 8px;
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
