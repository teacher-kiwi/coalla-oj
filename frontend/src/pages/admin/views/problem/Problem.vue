<template>
  <div class="problem">
    <Panel :title="title">
      <el-form ref="formRef" :model="problem" :rules="rules" label-position="top" label-width="70px">
        <el-row :gutter="20">
          <el-col :span="6">
            <el-form-item prop="_id" :label="t('m.Display_ID')"
                          :required="routeName === 'create-contest-problem' || routeName === 'edit-contest-problem'">
              <el-input :placeholder="t('m.Display_ID')" v-model="problem._id" />
            </el-form-item>
          </el-col>
          <el-col :span="18">
            <el-form-item prop="title" :label="t('m.Title')" required>
              <el-input :placeholder="t('m.Title')" v-model="problem.title" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="24">
            <el-form-item prop="description" :label="t('m.Description')" required>
              <Simditor v-model="problem.description" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="24">
            <el-form-item prop="input_description" :label="t('m.Input_Description')" required>
              <Simditor v-model="problem.input_description" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item prop="output_description" :label="t('m.Output_Description')" required>
              <Simditor v-model="problem.output_description" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item :label="t('m.Time_Limit') + ' (ms)'" required>
              <el-input type="number" :placeholder="t('m.Time_Limit')" v-model="problem.time_limit" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="t('m.Memory_limit') + ' (MB)'" required>
              <el-input type="number" :placeholder="t('m.Memory_limit')" v-model="problem.memory_limit" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="t('m.Difficulty')">
              <el-select class="difficulty-select" size="small" :placeholder="t('m.Difficulty')" v-model="problem.difficulty">
                <el-option :label="t('m.Low')" value="Low" />
                <el-option :label="t('m.Mid')" value="Mid" />
                <el-option :label="t('m.High')" value="High" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="4">
            <el-form-item :label="t('m.Visible')">
              <el-switch v-model="problem.visible" />
            </el-form-item>
          </el-col>
          <el-col :span="4">
            <el-form-item :label="t('m.ShareSubmission')">
              <el-switch v-model="problem.share_submission" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="t('m.Tag')" :error="error.tags" required>
              <span class="tags">
                <el-tag v-for="tag in problem.tags" :key="tag" closable type="success" @close="closeTag(tag)">
                  {{ tag }}
                </el-tag>
              </span>
              <el-autocomplete v-if="inputVisible" size="small" class="input-new-tag"
                               popper-class="problem-tag-poper" v-model="tagInput"
                               :trigger-on-focus="false" @keyup.enter="addTag"
                               @select="addTag" :fetch-suggestions="querySearch" />
              <el-button v-else class="button-new-tag" size="small" @click="inputVisible = true">
                + {{ t('m.New_Tag') }}
              </el-button>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="t('m.Languages')" :error="error.languages" required>
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
                <el-button type="warning" size="small" :icon="Delete" @click="deleteSample(index)">Delete</el-button>
              </template>
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item :label="t('m.Input_Samples')" required>
                    <el-input :rows="5" type="textarea" :placeholder="t('m.Input_Samples')" v-model="sample.input" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item :label="t('m.Output_Samples')" required>
                    <el-input :rows="5" type="textarea" :placeholder="t('m.Output_Samples')" v-model="sample.output" />
                  </el-form-item>
                </el-col>
              </el-row>
            </Accordion>
          </el-form-item>
        </div>
        <div class="add-sample-btn">
          <button type="button" class="add-samples" @click="addSample">
            <el-icon class="add-icon"><Plus /></el-icon>{{ t('m.Add_Sample') }}
          </button>
        </div>

        <el-form-item class="hint-item" :label="t('m.Hint')">
          <Simditor v-model="problem.hint" placeholder="" />
        </el-form-item>

        <el-form-item :label="t('m.Code_Template')">
          <el-row class="full-width">
            <el-col :span="24" v-for="(v, k) in template" :key="'template' + k">
              <el-checkbox v-model="v.checked">{{ k }}</el-checkbox>
              <div v-if="v.checked" class="full-width">
                <code-mirror v-model="v.code" :mode="v.mode" />
              </div>
            </el-col>
          </el-row>
        </el-form-item>

        <el-form-item :label="t('m.Special_Judge')" :error="error.spj">
          <el-col :span="24">
            <el-checkbox :model-value="problem.spj" @click.prevent="switchSpj">{{ t('m.Use_Special_Judge') }}</el-checkbox>
          </el-col>
        </el-form-item>
        <el-form-item v-if="problem.spj">
          <Accordion :title="t('m.Special_Judge_Code')">
            <template #header>
              <span>{{ t('m.SPJ_language') }}</span>
              <el-radio-group v-model="problem.spj_language">
                <el-tooltip v-for="lang in allLanguage.spj_languages" :key="lang.name"
                            class="spj-radio" effect="dark" :content="lang.description" placement="top-start">
                  <el-radio :label="lang.name">{{ lang.name }}</el-radio>
                </el-tooltip>
              </el-radio-group>
              <el-button type="primary" size="small" @click="compileSPJ" :loading="loadingCompile">
                {{ t('m.Compile') }}
              </el-button>
            </template>
            <code-mirror v-model="problem.spj_code" :mode="spjMode" />
          </Accordion>
        </el-form-item>

        <el-row :gutter="20">
          <el-col :span="4">
            <el-form-item :label="t('m.Type')">
              <el-radio-group v-model="problem.rule_type" :disabled="disableRuleType">
                <el-radio label="ACM">ACM</el-radio>
                <el-radio label="OI">OI</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item :label="t('m.TestCase')" :error="error.testCase">
              <el-upload action="/api/admin/test_case" name="file" :data="{ spj: problem.spj }"
                         :show-file-list="true" :on-success="uploadSucceeded" :on-error="uploadFailed">
                <el-button size="small" type="primary">Choose File</el-button>
              </el-upload>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item :label="t('m.IOMode')">
              <el-radio-group v-model="problem.io_mode.io_mode">
                <el-radio label="Standard IO">Standard IO</el-radio>
                <el-radio label="File IO">File IO</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="4" v-if="problem.io_mode.io_mode === 'File IO'">
            <el-form-item :label="t('m.InputFileName')" required>
              <el-input v-model="problem.io_mode.input" />
            </el-form-item>
          </el-col>
          <el-col :span="4" v-if="problem.io_mode.io_mode === 'File IO'">
            <el-form-item :label="t('m.OutputFileName')" required>
              <el-input v-model="problem.io_mode.output" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-table :data="problem.test_case_score" class="full-width">
              <el-table-column prop="input_name" :label="t('m.Input')" />
              <el-table-column prop="output_name" :label="t('m.Output')" />
              <el-table-column prop="score" :label="t('m.Score')">
                <template #default="{ row }">
                  <el-input size="small" :placeholder="t('m.Score')" v-model="row.score"
                            :disabled="problem.rule_type !== 'OI'" />
                </template>
              </el-table-column>
            </el-table>
          </el-col>
        </el-row>

        <el-form-item :label="t('m.Source')">
          <el-input :placeholder="t('m.Source')" v-model="problem.source" />
        </el-form-item>
        <save @click="submit">Save</save>
      </el-form>
    </Panel>
  </div>
</template>

<script setup>
import { ref, reactive, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import Simditor from '../../components/Simditor.vue'
import Accordion from '../../components/Accordion.vue'
import CodeMirror from '../../components/CodeMirror.vue'
import api from '../../api.js'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const formRef = ref(null)
const rules = {
  _id: { required: true, message: 'Display ID is required', trigger: 'blur' },
  title: { required: true, message: 'Title is required', trigger: 'blur' },
  input_description: { required: true, message: 'Input Description is required', trigger: 'blur' },
  output_description: { required: true, message: 'Output Description is required', trigger: 'blur' }
}

const loadingCompile = ref(false)
const mode = ref('')
const contest = ref({})
const testCaseUploaded = ref(false)
const allLanguage = ref({})
const inputVisible = ref(false)
const tagInput = ref('')
const template = ref({})
const title = ref('')
const spjMode = ref('')
const disableRuleType = ref(false)
const routeName = ref('')
const error = reactive({ tags: '', spj: '', languages: '', testCase: '' })

function defaultProblem () {
  return {
    _id: '', title: '', description: '', input_description: '', output_description: '',
    time_limit: 1000, memory_limit: 256, difficulty: 'Low', visible: true, share_submission: false,
    tags: [], languages: [], template: {}, samples: [{ input: '', output: '' }],
    spj: false, spj_language: '', spj_code: '', spj_compile_ok: false,
    test_case_id: '', test_case_score: [], rule_type: 'ACM', hint: '', source: '',
    io_mode: { io_mode: 'Standard IO', input: 'input.txt', output: 'output.txt' }
  }
}

const problem = ref(defaultProblem())

onMounted(() => {
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
      title.value = t('m.Edit_Problem')
      const funcName = { 'edit-problem': 'getProblem', 'edit-contest-problem': 'getContestProblem' }[routeName.value]
      api[funcName](route.params.problemId).then(problemRes => {
        const data = problemRes.data.data
        if (!data.spj_code) data.spj_code = ''
        data.spj_language = data.spj_language || 'C'
        problem.value = data
        testCaseUploaded.value = true
      })
    } else {
      title.value = t('m.Add_Problem')
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
    ElMessageBox.confirm('If you change problem judge method, you need to re-upload test cases', 'Warning', {
      confirmButtonText: 'Yes', cancelButtonText: 'Cancel', type: 'warning'
    }).then(() => {
      problem.value.spj = !problem.value.spj
      resetTestCase()
    }).catch(() => {})
  } else {
    problem.value.spj = !problem.value.spj
  }
}

function querySearch (queryString, cb) {
  api.getProblemTagList({ keyword: queryString }).then(res => {
    cb(res.data.data.map(tag => ({ value: tag.name })))
  }).catch(() => {})
}

function resetTestCase () {
  testCaseUploaded.value = false
  problem.value.test_case_score = []
  problem.value.test_case_id = ''
}

function addTag () {
  if (tagInput.value) problem.value.tags.push(tagInput.value)
  inputVisible.value = false
  tagInput.value = ''
}

function closeTag (tag) {
  problem.value.tags.splice(problem.value.tags.indexOf(tag), 1)
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

function uploadFailed () { ElMessage.error('Upload failed') }

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
    ElMessageBox.alert(err.data?.data || 'Compile error', 'Compile Error', { type: 'error', customClass: 'dialog-compile-error' })
  })
}

function submit () {
  if (!problem.value.samples.length) { ElMessage.error('Sample is required'); return }
  for (const sample of problem.value.samples) {
    if (!sample.input || !sample.output) { ElMessage.error('Sample input and output is required'); return }
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
        ElMessage.error('Invalid test case score'); return
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
  .input-new-tag { width: 78px; }
  .button-new-tag { height: 24px; line-height: 22px; padding-top: 0; padding-bottom: 0; }
  .tags { .el-tag { margin-right: 10px; } }
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
.problem-tag-poper { width: 200px !important; }
.dialog-compile-error { width: auto; max-width: 80%; overflow-x: scroll; }
</style>
