<template>
  <Panel shadow :padding="20">
    <!-- 폼 화면이라 여백을 준다. 안의 테스트케이스 표도 입력칸이라 폼과 같이 들여쓴다.
         (이 주석은 루트 밖으로 내면 안 된다. 루트가 요소 하나가 아니라 프래그먼트가
          되어 App.vue 의 transition mode="out-in" 이 이 화면을 끝내 못 떠나고,
          다음 화면이 mount 되지 않아 빈 화면이 된다. check-single-root.mjs 가 막는다) -->
    <template #title>{{ isEdit ? '문제 수정' : '문제 만들기' }}</template>

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

    <hr />
    <el-form label-position="top" class="judge-form">
      <el-form-item label="채점 방식">
        <el-radio-group v-model="form.spj">
          <el-radio :value="false">일반</el-radio>
          <el-radio :value="true">스페셜 저지</el-radio>
        </el-radio-group>
        <p class="guide form-item-row">
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
        <el-input v-model="form.spj_code" type="textarea" :rows="8" class="spj-code form-item-row"
                  placeholder="입력 파일과 학생 출력 파일을 인자로 받아, 맞으면 0 틀리면 1 로 끝내세요" />
        <p class="guide form-item-row">
          저장할 때 컴파일해 봅니다. 컴파일되지 않으면 저장되지 않습니다.
        </p>
      </el-form-item>
    </el-form>

    <div class="cases">
      <div class="cases-head">
        <span class="cases-title">테스트 케이스</span>
        <el-upload :action="uploadUrl" name="file" :data="{ spj: String(form.spj) }"
                   :show-file-list="false" :with-credentials="true"
                   :before-upload="onUploadStart"
                   :on-success="onUploaded" :on-error="onUploadFailed">
          <el-button size="small" :loading="uploading">zip 파일로 채우기</el-button>
        </el-upload>
        <el-button size="small" :icon="Plus" :disabled="typedCount >= MAX_CASES"
                   @click="addCase">케이스 추가</el-button>
      </div>
      <p class="guide">
        학생이 제출한 소스코드를 검증할 입력과 출력을 적습니다.<br />
        줄을 펼쳐서 고칠 수 있고, 직접 입력하는 것은 {{ MAX_CASES }}개까지입니다(zip 은 개수 제한이 없습니다).<br />
        zip 으로 제출한 케이스 중 너무 긴 케이스는 여기서 고칠 수 없고 그대로 유지됩니다.
        <template v-if="form.spj"><br />단, 스페셜 저지는 판정 코드가 정하므로 출력을 넣지 않습니다.</template>
      </p>

      <el-table :data="cases" class="full-width" size="small" row-key="key">
        <el-table-column type="expand">
          <template #default="{ row }">
            <div v-if="row.too_large" class="case-locked">
              내용이 커서 여기서 고칠 수 없습니다. 저장해도 그대로 유지됩니다.
            </div>
            <!-- el-row 의 gutter 는 음수 마진으로 만들어져 제 칸보다 넓어진다.
                 표의 펼침 칸 안에서는 그만큼 표가 가로로 스크롤된다. -->
            <div v-else class="case-editor">
              <el-input v-model="row.input" type="textarea" :rows="5" placeholder="입력" />
              <el-input v-if="!form.spj" v-model="row.output" type="textarea" :rows="5"
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
        <el-table-column v-if="!form.spj" label="출력">
          <template #default="{ row }"><span class="case-peek">{{ peek(row, 'output') }}</span></template>
        </el-table-column>
        <el-table-column width="70" align="center">
          <template #default="{ $index }">
            <el-button size="small" type="danger" link :disabled="cases.length === 1"
                       @click="cases.splice($index, 1)">삭제</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <span>케이스가 없습니다. "케이스 추가" 나 "zip 파일로 채우기" 를 쓰세요.</span>
        </template>
      </el-table>

    </div>

    <el-form label-position="top" class="judge-form">
      <el-form-item>
        <!-- 안 쓰는 사람이 대부분이라 접어 둔다. 체크를 풀면 코드도 지운다
             (남겨 두면 저장할 때 함께 올라가 무엇이 저장되는지 어긋난다) -->
        <el-checkbox v-model="useSolver" @change="onUseSolverChange">
          정답 코드 사용하기 (테스트 케이스 검증용)
        </el-checkbox>
      </el-form-item>
      <el-form-item v-if="useSolver">
        <el-select v-model="form.solver_language" placeholder="언어" clearable
                   class="spj-language">
          <el-option v-for="lang in languages" :key="lang" :value="lang" :label="lang" />
        </el-select>
        <el-input v-model="form.solver_code" type="textarea" :rows="8" class="spj-code form-item-row"
                  placeholder="이 문제의 정답 코드를 넣으면 테스트 케이스가 맞는지 확인할 수 있습니다" />
        <div class="verify-row form-item-row">
          <el-button size="small" :loading="verifying" :disabled="!form.solver_code"
                     @click="verify">테스트 케이스 확인</el-button>
          <span v-if="verifyMessage" :class="['verify-message', { bad: verifyFailed }]">
            {{ verifyMessage }}
          </span>
        </div>
        <p class="guide form-item-row">
          넣어 둔 출력과 정답 코드의 결과가 같은지 봅니다. 저장과는 따로 돌고,
          통과하지 못해도 저장할 수 있습니다. 넣지 않아도 됩니다.<br />
          테스트 케이스가 잘못되면 학생이 제대로 풀어도 오답이 나오는데, 학생은
          자기 코드를 의심하지 문제를 의심하지 않습니다.
        </p>
      </el-form-item>

    </el-form>

    <hr />
    <div class="cases">
      <div class="cases-head">
        <span class="cases-title">예제</span>
        <el-button size="small" :icon="Plus" :disabled="samples.length >= MAX_SAMPLES"
                   @click="samples.push(newSample())">예제 추가</el-button>
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
        <el-table-column label="테스트 케이스 사용하기" width="150">
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

    <!-- 다 적고 나면 바로 누를 수 있게 맨 아래에 둔다(관리자 출제 화면과 같다).
         목록으로는 브라우저 뒤로가기로 돌아간다. 이 화면은 목록에서만 들어온다. -->
    <div class="save-row">
      <el-button type="primary" :loading="saving" @click="save">저장</el-button>
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
// 예제 하나의 크기 상한(서버의 MAX_SAMPLE_BYTES 와 같아야 한다).
// 예제는 문제를 여는 모든 학생에게 매번 전송된다.
const MAX_SAMPLE_BYTES = MAX_SAMPLE_KB * 1024
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
  spj: false, spj_language: '', spj_code: '',
  solver_language: '', solver_code: ''
})
// newCase() 가 이 값을 쓴다. ref 초기값이 setup 실행 중에 만들어지므로
// 선언이 뒤에 있으면 TDZ 에 걸린다.
let caseKey = 0
const cases = ref([newCase()])
const uploading = ref(false)
const samples = ref([newSample()])
const spjLanguages = ref([])
const languages = ref([])
// 정답 코드 칸을 펼쳐 둘지. 저장된 코드가 있으면 열린 채로 시작한다.
const useSolver = ref(false)
const verifying = ref(false)
const verifyMessage = ref('')
const verifyFailed = ref(false)
let verifyTimer = null
const verificationToken = ref('')
const uploadUrl = '/api/teacher/problem/test_case'

// 예제는 여기서 골라 채운다. 표에 있는 케이스가 곧 후보다.
const pickableCases = computed(() => cases.value.map((c, index) => ({
  index: index + 1,
  input: c.input,
  // 스페셜 저지는 출력 칸이 없다. null 이면 예제 출력을 건드리지 않는다.
  output: form.spj ? null : c.output,
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

// 표에는 한 줄만 보여준다. 펼치면 전부 고칠 수 있다.
function peek (row, field) {
  if (row.too_large) return `${row[field + '_size']}바이트 (여기서 고칠 수 없음)`
  const text = (row[field] || '').trim()
  if (!text) return '(비어 있음)'
  const first = text.split('\n')[0]
  return first.length > 40 ? first.slice(0, 40) + '…' : first
}

// 서버가 준 케이스로 표를 채운다. loaded 를 남겨 두어 "고쳤나" 를 알 수 있다.
function fillCases (loaded) {
  cases.value = loaded.map(c => ({
    key: ++caseKey,
    index: c.index,
    input: c.input || '',
    output: c.output || '',
    too_large: c.too_large,
    input_size: c.input_size,
    output_size: c.output_size,
    loaded: c.too_large ? null : { input: c.input || '', output: c.output || '' }
  }))
  if (!cases.value.length) cases.value = [newCase()]
}

watch([form, cases, samples], () => {
  if (watching) dirty.value = true
}, { deep: true })

function newCase () {
  return { key: ++caseKey, index: null, input: '', output: '', too_large: false,
    input_size: 0, output_size: 0, loaded: null }
}

function newSample () {
  return { input: '', output: '' }
}

// 지금 폼이 들고 있는 테스트 케이스. 저장할 때와 같은 것을 검증에도 보낸다.
// 못 고치는 것과 손대지 않은 것은 번호만 보낸다 - 서버가 이전 파일을 그대로 쓴다.
function casePayload () {
  return {
    cases: cases.value
      .filter(c => c.too_large || c.loaded || c.input.trim() || c.output.trim())
      .map(c => (isTyped(c) ? { input: c.input, output: c.output } : { keep: c.index }))
  }
}

function onUseSolverChange (on) {
  if (on) return
  form.solver_language = ''
  form.solver_code = ''
  verifyMessage.value = ''
  verificationToken.value = ''
}

function verify () {
  const payload = {
    ...casePayload(),
    // keep 으로 보낸 케이스를 서버가 이 문제의 것에서 찾아 쓴다
    problem_id: isEdit.value ? Number(problemId) : undefined,
    solver_language: form.solver_language,
    solver_code: form.solver_code,
    spj: form.spj,
    spj_language: form.spj_language,
    spj_code: form.spj_code
  }
  if (!payload.cases?.length && !payload.test_case_id) {
    ElMessage.error('테스트 케이스를 먼저 넣어주세요')
    return
  }
  verifying.value = true
  verifyFailed.value = false
  verifyMessage.value = '확인하는 중입니다…'
  api.verifyTeacherSolution(payload).then(res => {
    verificationToken.value = res.data.data.token
    pollVerification()
  }, () => {
    verifying.value = false
    verifyMessage.value = ''
  })
}

// 채점 서버가 바쁘면 자리가 날 때까지 기다리므로 결과가 늦을 수 있다
function pollVerification () {
  verifyTimer = setTimeout(() => {
    api.getTeacherVerification(verificationToken.value).then(res => {
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

function addCase () {
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
  // 올린 케이스로 표를 채운다. 여기서 바로 고칠 수 있다.
  fillCases(response.data.cases)
  ElMessage.success(`케이스 ${response.data.info.length}개를 채웠습니다`)
}

function onUploadFailed () {
  uploading.value = false
  ElMessage.error('업로드에 실패했습니다')
}

function goList () {
  router.push({ name: 'teacher-problem-list' })
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
  if (!casePayload().cases.length) return '테스트 케이스를 하나 이상 넣어주세요'
  if (typedCount.value > MAX_CASES) {
    return `직접 쳐 넣는 테스트 케이스는 ${MAX_CASES}개까지입니다`
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
  // 검증해 둔 것이 있으면 표를 함께 보낸다. 그사이 케이스를 고쳤으면 서버가
  // 지문을 대조해 붙이지 않는다.
  if (verificationToken.value) data.verification_token = verificationToken.value
  // 케이스는 늘 전부 보낸다. 고치지 않은 것은 번호만 가고, 내용이 예전과 같으면
  // 서버가 파일을 갈아끼우지 않으므로 재채점도 돌지 않는다.
  Object.assign(data, casePayload())

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

onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', warnBeforeUnload)
  // 화면을 떠나면 검증 결과는 필요 없다. 캐시에 남은 것은 시간이 지나 사라진다.
  clearTimeout(verifyTimer)
})

onMounted(() => {
  window.addEventListener('beforeunload', warnBeforeUnload)
  api.getAllProblemTags().then(res => { tagOptions.value = res.data.data }, () => {})
  api.getLanguages().then(res => {
    spjLanguages.value = (res.data.data.spj_languages || []).map(lang => lang.name)
    languages.value = (res.data.data.languages || []).map(lang => lang.name)
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
      spj: p.spj, spj_language: p.spj_language || '', spj_code: p.spj_code || '',
      solver_language: p.solver_language || '', solver_code: p.solver_code || ''
    })
    useSolver.value = !!p.solver_code
    api.getTeacherTestCases(problemId).then(res => fillCases(res.data.data.cases), () => {})
    if (p.solver_verified_at) {
      verifyFailed.value = !p.solver_passed
      verifyMessage.value = p.solver_message
    }
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

.save-row {
  margin-top: 24px;
}

.guide {
  font-size: 12px;
  color: #909399;
  line-height: 1.8;
  margin-top: 0;
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

.verify-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 8px;
}

.case-editor {
  display: flex;
  gap: 12px;
  padding: 4px 0;

  // 기본값 auto 면 안의 글이 길 때 칸이 줄지 않아 표가 가로로 넘친다
  > * {
    flex: 1;
    min-width: 0;
  }
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

.verify-message {
  font-size: 13px;
  color: #67c23a;
  white-space: pre-line;

  &.bad {
    color: #e6a23c;
  }
}
</style>
