<template>
  <div class="problem">
    <Panel :title="title">
      <el-form ref="formRef" :model="problem" :rules="rules" label-position="top" label-width="70px">
        <el-row :gutter="20">
          <el-col :span="6">
            <el-form-item prop="_id" label="표시 ID"
                          :required="routeName === 'create-contest-problem' || routeName === 'edit-contest-problem'">
              <el-input placeholder="표시 ID" v-model="problem._id" />
            </el-form-item>
          </el-col>
          <el-col :span="18">
            <el-form-item prop="title" label="제목" required>
              <el-input placeholder="제목" v-model="problem.title" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="24">
            <el-form-item prop="description" label="설명" required>
              <Simditor v-model="problem.description" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="24">
            <el-form-item prop="input_description" label="입력 설명" required>
              <Simditor v-model="problem.input_description" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item prop="output_description" label="출력 설명" required>
              <Simditor v-model="problem.output_description" />
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
                <el-option label="낮음" value="Low" />
                <el-option label="중간" value="Mid" />
                <el-option label="높음" value="High" />
              </el-select>
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
            </Accordion>
          </el-form-item>
        </div>
        <div class="add-sample-btn">
          <button type="button" class="add-samples" @click="addSample">
            <el-icon class="add-icon"><Plus /></el-icon>예제 추가
          </button>
        </div>

        <el-form-item class="hint-item" label="힌트">
          <Simditor v-model="problem.hint" placeholder="" />
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
              <el-radio-group v-model="problem.rule_type" :disabled="disableRuleType">
                <el-radio label="ACM">ACM</el-radio>
                <el-radio label="OI">OI</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="테스트 케이스" :error="error.testCase">
              <el-upload action="/api/admin/test_case" name="file" :data="{ spj: problem.spj }"
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
          <el-col :span="24">
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
import { ref, reactive, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import Simditor from '../../components/Simditor.vue'
import Accordion from '../../components/Accordion.vue'
import CodeMirror from '../../components/CodeMirror.vue'
import api from '../../api.js'
const route = useRoute()
const router = useRouter()

const formRef = ref(null)
const rules = {
  _id: { required: true, message: '표시 ID를 입력하세요', trigger: 'blur' },
  title: { required: true, message: '제목을 입력하세요', trigger: 'blur' },
  description: { required: true, message: '설명을 입력하세요', trigger: 'blur' },
  input_description: { required: true, message: '입력 설명을 입력하세요', trigger: 'blur' },
  output_description: { required: true, message: '출력 설명을 입력하세요', trigger: 'blur' }
}

const loadingCompile = ref(false)
const tagLoading = ref(false)
const mode = ref('')
const contest = ref({})
const testCaseUploaded = ref(false)
const allLanguage = ref({})
const tagOptions = ref([])
const template = ref({})
const title = ref('')
const spjMode = ref('')
const disableRuleType = ref(false)
const routeName = ref('')
const error = reactive({ tags: '', spj: '', languages: '', testCase: '' })

function defaultProblem () {
  return {
    _id: '', title: '', description: '', input_description: '', output_description: '',
    time_limit: 1000, memory_limit: 256, difficulty: 'Low', visible: true,
    tags: [], languages: [], template: {}, samples: [{ input: '', output: '' }],
    spj: false, spj_language: '', spj_code: '', spj_compile_ok: false,
    test_case_id: '', test_case_score: [], rule_type: 'ACM', hint: '', source: '',
    io_mode: { io_mode: 'Standard IO', input: 'input.txt', output: 'output.txt' }
  }
}

const problem = ref(defaultProblem())

onMounted(() => {
  getTagOptions()
  routeName.value = route.name
  mode.value = (routeName.value === 'edit-problem' || routeName.value === 'edit-contest-problem') ? 'edit' : 'add'

  api.getLanguages().then(res => {
    problem.value = defaultProblem()

    const contestID = route.params.contestId
    if (contestID) {
      problem.value.contest_id = contestID
      disableRuleType.value = true
      api.getContest(contestID).then(cRes => {
        problem.value.rule_type = cRes.data.data.rule_type
        contest.value = cRes.data.data
      })
    }

    problem.value.spj_language = 'C'
    allLanguage.value = res.data.data

    if (mode.value === 'edit') {
      title.value = '문제 수정'
      const funcName = { 'edit-problem': 'getProblem', 'edit-contest-problem': 'getContestProblem' }[routeName.value]
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
  if (!testCaseUploaded.value) { error.testCase = 'Test case is not uploaded yet'; ElMessage.error(error.testCase); return }
  if (problem.value.rule_type === 'OI') {
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

  const funcName = {
    'create-problem': 'createProblem', 'edit-problem': 'editProblem',
    'create-contest-problem': 'createContestProblem', 'edit-contest-problem': 'editContestProblem'
  }[routeName.value]

  if (funcName === 'editContestProblem') problem.value.contest_id = contest.value.id

  api[funcName](problem.value).then(() => {
    if (routeName.value === 'create-contest-problem' || routeName.value === 'edit-contest-problem') {
      router.push({ name: 'contest-problem-list', params: { contestId: route.params.contestId } })
    } else {
      router.push({ name: 'problem-list' })
    }
  }).catch(() => {})
}
</script>

<style lang="less" scoped>
.problem {
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
