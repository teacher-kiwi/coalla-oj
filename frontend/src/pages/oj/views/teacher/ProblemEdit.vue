<template>
  <Panel shadow :padding="20">
    <!-- 폼 화면이라 여백을 준다. 안의 테스트케이스 표도 입력칸이라 폼과 같이 들여쓴다.
         (이 주석은 루트 밖으로 내면 안 된다. 루트가 요소 하나가 아니라 프래그먼트가
          되어 App.vue 의 transition mode="out-in" 이 이 화면을 끝내 못 떠나고,
          다음 화면이 mount 되지 않아 빈 화면이 된다. check-single-root.mjs 가 막는다) -->
    <template #title>{{ isEdit ? '문제 수정' : '문제 만들기' }}</template>
    <template #extra>
      <el-button @click="goList">목록</el-button>
      <el-button type="primary" :loading="saving" @click="save">저장</el-button>
    </template>

    <el-form label-position="top" v-loading="loading">
      <el-form-item label="제목" required>
        <el-input v-model="form.title" maxlength="100" show-word-limit
                  placeholder="예: 두 수의 합" />
      </el-form-item>

      <el-form-item label="문제 설명" required>
        <MarkdownEditor v-model="form.description" />
      </el-form-item>

      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="입력 설명">
            <el-input v-model="form.input_description" type="textarea" :rows="3"
                      placeholder="예: 첫째 줄에 두 정수가 공백으로 주어집니다" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="출력 설명">
            <el-input v-model="form.output_description" type="textarea" :rows="3"
                      placeholder="예: 두 수의 합을 출력합니다" />
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="16">
        <el-col :span="8">
          <el-form-item label="난이도" required>
            <el-select v-model="form.difficulty" class="full-width">
              <el-option v-for="d in DIFFICULTY" :key="d.value" :value="d.value" :label="d.label">
                <span :style="{ color: d.color }">{{ d.label }}</span>
                <span class="option-guide">{{ DIFFICULTY_GUIDE[d.value] }}</span>
              </el-option>
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="16">
          <el-form-item label="태그" required>
            <el-select v-model="form.tags" multiple filterable class="full-width"
                       placeholder="이 문제로 무엇을 연습하나요?">
              <el-option v-for="tag in tagOptions" :key="tag.name"
                         :value="tag.name" :label="tag.name" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>

      <el-form-item label="힌트">
        <el-input v-model="form.hint" type="textarea" :rows="2"
                  placeholder="학생에게 보여줄 힌트가 있으면 적어주세요" />
      </el-form-item>
    </el-form>

    <el-form label-position="top" class="judge-form">
      <el-form-item label="채점 방식">
        <el-radio-group v-model="form.spj" @change="onSpjChange">
          <el-radio :value="false">일반</el-radio>
          <el-radio :value="true">스페셜 저지</el-radio>
        </el-radio-group>
        <p class="guide">
          <template v-if="form.spj">
            답이 여럿인 문제입니다("4보다 작은 수를 모두 출력" 처럼 순서가 달라도 정답).
            정답 파일 대신 아래 판정 코드가 맞고 틀림을 정합니다.
          </template>
          <template v-else>
            정답이 하나로 정해지는 보통의 문제입니다. 넣어둔 출력과 똑같으면 정답입니다.
          </template>
        </p>
      </el-form-item>

      <el-form-item v-if="form.spj" label="판정 코드" required>
        <el-select v-model="form.spj_language" placeholder="언어" class="spj-language">
          <el-option v-for="lang in spjLanguages" :key="lang" :value="lang" :label="lang" />
        </el-select>
        <el-input v-model="form.spj_code" type="textarea" :rows="8" class="spj-code"
                  placeholder="입력 파일과 학생 출력 파일을 인자로 받아, 맞으면 0 틀리면 1 로 끝내세요" />
        <p class="guide">
          저장할 때 컴파일해 봅니다. 컴파일되지 않으면 저장되지 않습니다.
        </p>
      </el-form-item>
    </el-form>

    <div class="cases">
      <div class="cases-head">
        <span class="cases-title">테스트 케이스</span>
        <el-radio-group v-model="caseSource" size="small" @change="onSourceChange">
          <el-radio-button value="manual">직접 입력</el-radio-button>
          <el-radio-button value="file">파일 올리기</el-radio-button>
        </el-radio-group>
        <el-button v-if="caseSource === 'manual'" size="small" :icon="Plus"
                   :disabled="cases.length >= MAX_CASES" @click="addCase">케이스 추가</el-button>
      </div>

      <template v-if="caseSource === 'manual'">
        <p class="guide">
          입력을 넣으면 이 답이 나와야 한다는 짝을 적습니다.
          최대 {{ MAX_CASES }}개까지 넣을 수 있고, 더 많으면 파일로 올리세요.
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
          <el-table-column v-if="!form.spj" label="출력">
            <template #default="{ row }">
              <el-input v-model="row.output" type="textarea" :rows="3" placeholder="출력" />
            </template>
          </el-table-column>
          <el-table-column width="70" align="center">
            <template #default="{ $index }">
              <el-button size="small" type="danger" link :disabled="cases.length === 1"
                         @click="cases.splice($index, 1)">삭제</el-button>
            </template>
          </el-table-column>
        </el-table>
      </template>

      <template v-else>
        <p class="guide">
          1.in, 1.out, 2.in, 2.out … 을 담은 zip 파일을 올립니다.
          <template v-if="form.spj">스페셜 저지는 정답 파일 없이 1.in, 2.in … 만 넣습니다.</template>
        </p>
        <el-upload :action="uploadUrl" name="file" :data="{ spj: String(form.spj) }"
                   :show-file-list="false" :with-credentials="true"
                   :before-upload="onUploadStart"
                   :on-success="onUploaded" :on-error="onUploadFailed">
          <el-button size="small" type="primary" :loading="uploading">zip 파일 선택</el-button>
        </el-upload>
        <p v-if="uploaded" class="guide">
          케이스 {{ uploaded.info.length }}개를 올렸습니다.
        </p>
      </template>

      <p v-if="isEdit && !casesTouched" class="guide">
        테스트 케이스를 고치지 않고 저장하면 기존 케이스가 그대로 유지됩니다.
      </p>
    </div>

    <div class="cases">
      <div class="cases-head">
        <span class="cases-title">예제</span>
        <el-button size="small" :icon="Plus" :disabled="samples.length >= MAX_SAMPLES"
                   @click="samples.push(newSample())">예제 추가</el-button>
        <el-button v-if="isEdit" size="small" :loading="loadingPreview"
                   @click="loadSavedCases">저장된 케이스 불러오기</el-button>
      </div>
      <p class="guide">
        문제 화면에 그대로 나오는 예시입니다(최대 {{ MAX_SAMPLES }}개, 각 {{ MAX_SAMPLE_KB }}KB).
        <b>가져오기</b>로 테스트 케이스의 내용을 채운 뒤 고칠 수 있습니다.
        <template v-if="form.spj">
          스페셜 저지는 정답이 여럿이라 입력만 가져오고 출력은 직접 적습니다.
        </template>
      </p>

      <el-table :data="samples" class="full-width" size="small">
        <el-table-column label="#" width="50" align="center">
          <template #default="{ $index }">{{ $index + 1 }}</template>
        </el-table-column>
        <el-table-column label="입력">
          <template #default="{ row }">
            <el-input v-model="row.input" type="textarea" :rows="3" placeholder="입력" />
          </template>
        </el-table-column>
        <el-table-column label="출력">
          <template #default="{ row }">
            <el-input v-model="row.output" type="textarea" :rows="3" placeholder="출력" />
          </template>
        </el-table-column>
        <el-table-column label="가져오기" width="150">
          <template #default="{ row }">
            <el-select :model-value="null" placeholder="케이스" size="small"
                       :disabled="!pickableCases.length"
                       @change="fillSample(row, $event)">
              <el-option v-for="c in pickableCases" :key="c.index" :value="c.index"
                         :label="`${c.index}번`" :disabled="c.too_large" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column width="70" align="center">
          <template #default="{ $index }">
            <el-button size="small" type="danger" link :disabled="samples.length === 1"
                       @click="samples.splice($index, 1)">삭제</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </Panel>
</template>

<script setup>
import { ref, reactive, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '@oj/api'
import { DIFFICULTY, DIFFICULTY_GUIDE } from '@/utils/constants'
// 관리자 출제 화면과 같은 편집기를 쓴다
import MarkdownEditor from '@admin/components/MarkdownEditor.vue'

// 서버(problem/serializers.py)와 같은 값이어야 한다
const MAX_CASES = 20
const MAX_SAMPLES = 3
// 예제로 고르라고 보여주는 케이스 수(서버의 SAMPLE_PICK_LIMIT 과 같아야 한다)
const SAMPLE_PICK_LIMIT = 5
const MAX_SAMPLE_KB = 2

const route = useRoute()
const router = useRouter()
const problemId = route.params.problemId
const isEdit = computed(() => !!problemId)

const loading = ref(false)
const saving = ref(false)
const tagOptions = ref([])
const casesTouched = ref(false)
// 저장하지 않은 변경이 있는지. 화면을 벗어날 때 한 번 물어보기 위한 값이다.
const dirty = ref(false)
// 처음 값을 채워 넣는 동안의 변경은 사용자가 한 것이 아니다
let watching = false

const form = reactive({
  title: '', description: '', input_description: '', output_description: '',
  hint: '', difficulty: 'L1', tags: [],
  spj: false, spj_language: '', spj_code: ''
})
// 테스트 케이스를 넣는 두 가지 길. 섞을 수 없어 하나를 고른다.
const caseSource = ref('manual')
const cases = ref([newCase()])
const uploaded = ref(null)
const uploading = ref(false)
const samples = ref([newSample()])
const spjLanguages = ref([])
const loadingPreview = ref(false)
// 올린 케이스(파일)나 지금 치고 있는 케이스(직접 입력)에서 예제를 가져온다
const savedCases = ref([])
const uploadUrl = '/api/teacher/problem/test_case'

const pickableCases = computed(() => {
  if (caseSource.value === 'file') return uploaded.value ? uploaded.value.cases : savedCases.value
  return cases.value.slice(0, SAMPLE_PICK_LIMIT).map((c, index) => ({
    // 스페셜 저지는 출력 칸이 없다. null 이면 예제 출력을 건드리지 않는다.
    index: index + 1, input: c.input, output: form.spj ? null : c.output, too_large: false
  }))
})

watch([form, cases, samples], () => {
  if (watching) dirty.value = true
}, { deep: true })

function newCase () {
  return { input: '', output: '' }
}

function newSample () {
  return { input: '', output: '' }
}

function addCase () {
  casesTouched.value = true
  cases.value.push(newCase())
}

// 케이스 내용을 예제 칸에 복사한다. 그 뒤 고치는 것은 교사 몫이다.
function fillSample (row, index) {
  const picked = pickableCases.value.find(c => c.index === index)
  if (!picked) return
  row.input = picked.input || ''
  // 스페셜 저지는 정답 파일이 없다. 여러 정답 중 하나를 교사가 적어야 한다.
  if (picked.output !== null && picked.output !== undefined) row.output = picked.output
}

function onSpjChange () {
  // 채점 방식이 바뀌면 올려둔 케이스는 짝이 맞지 않는다(정답 파일 유무가 다르다)
  uploaded.value = null
  savedCases.value = []
}

function onSourceChange () {
  casesTouched.value = true
}

function onUploadStart () {
  uploading.value = true
  return true
}

function onUploaded (response) {
  uploading.value = false
  if (response.error) {
    ElMessage.error(response.data)
    return
  }
  uploaded.value = response.data
  casesTouched.value = true
  ElMessage.success(`케이스 ${response.data.info.length}개를 올렸습니다`)
}

function onUploadFailed () {
  uploading.value = false
  ElMessage.error('업로드에 실패했습니다')
}

// 고칠 때 이미 저장된 케이스에서 예제를 다시 고를 수 있게 한다
function loadSavedCases () {
  loadingPreview.value = true
  api.getTeacherTestCases(problemId).then(res => {
    loadingPreview.value = false
    savedCases.value = res.data.data.cases
    caseSource.value = 'file'
    casesTouched.value = false
    ElMessage.success('저장된 케이스를 불러왔습니다')
  }, () => {
    loadingPreview.value = false
  })
}

function goList () {
  router.push({ name: 'teacher-problem-list' })
}

function filledCases () {
  return cases.value.filter(c => c.input.trim() || c.output.trim())
}

function filledSamples () {
  return samples.value.filter(s => s.input.trim() || s.output.trim())
}

function validate () {
  if (!form.title.trim()) return '제목을 입력해주세요'
  if (!form.description.trim()) return '문제 설명을 입력해주세요'
  if (!form.tags.length) return '태그를 하나 이상 골라주세요'
  if (form.spj && !form.spj_code.trim()) return '판정 코드를 입력해주세요'
  if (form.spj && !form.spj_language) return '판정 코드의 언어를 골라주세요'
  if (!filledSamples().length) return '예제를 하나 이상 넣어주세요'
  if (caseSource.value === 'manual') {
    // 고칠 때 손대지 않았으면 기존 케이스를 그대로 둔다
    if (!filledCases().length && !(isEdit.value && !casesTouched.value)) {
      return '테스트 케이스를 하나 이상 넣어주세요'
    }
  } else if (!uploaded.value && (!isEdit.value || casesTouched.value)) {
    return '테스트 케이스 파일을 올려주세요'
  }
  return null
}

function save () {
  const error = validate()
  if (error) {
    ElMessage.error(error)
    return
  }
  const data = { ...form, hint: form.hint || '' }
  data.samples = filledSamples().map(s => ({ input: s.input, output: s.output }))
  // 편집 화면에서 케이스를 손대지 않았으면 보내지 않는다(서버가 기존 것을 유지한다)
  if (!isEdit.value || casesTouched.value) {
    if (caseSource.value === 'manual') {
      data.cases = filledCases().map(c => ({ input: c.input, output: c.output }))
    } else if (uploaded.value) {
      data.test_case_id = uploaded.value.id
    }
  }

  saving.value = true
  const request = isEdit.value
    ? api.editProblem({ ...data, id: Number(problemId) })
    : api.createProblem(data)
  request.then(() => {
    saving.value = false
    dirty.value = false
    if (isEdit.value && casesTouched.value) {
      // 테스트 케이스가 바뀌면 서버가 이 문제의 제출을 전부 다시 채점한다
      ElMessage.warning('테스트 케이스가 바뀌어 이 문제의 제출을 다시 채점합니다. ' +
        '정답률과 대회 순위는 채점이 끝난 뒤 반영됩니다.')
    } else {
      ElMessage.success(isEdit.value ? '수정했습니다' : '문제를 만들었습니다')
    }
    goList()
  }, () => {
    saving.value = false
  })
}

// 목록 버튼이나 브라우저 뒤로가기로 나갈 때
onBeforeRouteLeave(async () => {
  if (!dirty.value) return true
  try {
    await ElMessageBox.confirm(
      '저장하지 않은 내용이 있습니다. 나가면 지금까지 쓴 내용이 사라집니다.',
      '저장하지 않고 나가기',
      { confirmButtonText: '나가기', cancelButtonText: '계속 쓰기', type: 'warning' })
    return true
  } catch (e) {
    return false
  }
})

// 새로고침이나 창 닫기는 라우터가 잡지 못해 브라우저 기본 경고를 쓴다
function warnBeforeUnload (event) {
  if (!dirty.value) return
  event.preventDefault()
  event.returnValue = ''
}

onBeforeUnmount(() => window.removeEventListener('beforeunload', warnBeforeUnload))

onMounted(() => {
  window.addEventListener('beforeunload', warnBeforeUnload)
  api.getAllProblemTags().then(res => { tagOptions.value = res.data.data }, () => {})
  api.getLanguages().then(res => {
    spjLanguages.value = (res.data.data.spj_languages || []).map(lang => lang.name)
  }, () => {})
  if (!isEdit.value) {
    nextTick(() => { watching = true })
    return
  }

  loading.value = true
  api.getMyProblem(problemId).then(res => {
    loading.value = false
    const p = res.data.data
    Object.assign(form, {
      title: p.title, description: p.description,
      input_description: p.input_description, output_description: p.output_description,
      hint: p.hint || '', difficulty: p.difficulty, tags: p.tags,
      spj: p.spj, spj_language: p.spj_language || '', spj_code: p.spj_code || ''
    })
    // 저장된 예제는 되살린다. 채점용 케이스의 내용은 파일로만 있어 여기서
    // 부르지 않는다(클 수 있다). 필요하면 "저장된 케이스 불러오기" 로 가져온다.
    samples.value = (p.samples || []).map(sample => ({ ...sample }))
    if (!samples.value.length) samples.value = [newSample()]
    // 여기까지 채운 값은 사용자의 변경이 아니다
    nextTick(() => { watching = true })
  }, () => {
    loading.value = false
    nextTick(() => { watching = true })
  })
})
</script>

<style scoped lang="less">
.full-width {
  width: 100%;
}

.cases {
  margin-top: 10px;

  &-head {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 6px;
  }

  &-title {
    font-size: 14px;
    font-weight: 600;
  }
}

.guide {
  font-size: 12px;
  color: #909399;
  line-height: 1.8;
  margin-bottom: 10px;
}

.option-guide {
  margin-left: 10px;
  font-size: 12px;
  color: #909399;
}

// 채점 방식과 판정 코드. 위의 본문 폼과 이어지는 자리라 위 여백만 준다.
.judge-form {
  margin-top: 10px;
}

.spj-language {
  width: 160px;
  margin-bottom: 8px;
}

.spj-code {
  font-family: Consolas, Monaco, "Courier New", monospace;
}
</style>
