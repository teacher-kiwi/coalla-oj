<template>
  <Panel shadow>
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

    <div class="cases">
      <div class="cases-head">
        <span class="cases-title">테스트 케이스</span>
        <el-button size="small" :icon="Plus" :disabled="cases.length >= MAX_CASES"
                   @click="addCase">케이스 추가</el-button>
      </div>
      <p class="guide">
        입력을 넣으면 이 답이 나와야 한다는 짝을 적습니다. 최대 {{ MAX_CASES }}개까지 넣을 수 있습니다.<br />
        <b>예제로 보여주기</b>를 체크한 것은 문제 화면에 그대로 나옵니다
        (최대 {{ MAX_SAMPLES }}개, 각 {{ MAX_SAMPLE_KB }}KB).
        체크하지 않은 것은 채점에만 쓰이고 학생에게 보이지 않습니다.
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
        <el-table-column label="출력">
          <template #default="{ row }">
            <el-input v-model="row.output" type="textarea" :rows="3" placeholder="출력" />
          </template>
        </el-table-column>
        <el-table-column label="예제로 보여주기" width="130" align="center">
          <template #default="{ row }">
            <el-checkbox v-model="row.is_sample" />
          </template>
        </el-table-column>
        <el-table-column width="70" align="center">
          <template #default="{ $index }">
            <el-button size="small" type="danger" link :disabled="cases.length === 1"
                       @click="cases.splice($index, 1)">삭제</el-button>
          </template>
        </el-table-column>
      </el-table>

      <p v-if="isEdit && !casesTouched" class="guide">
        테스트 케이스를 고치지 않고 저장하면 기존 케이스가 그대로 유지됩니다.
      </p>
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
// 마크다운 편집기는 관리자 출제 화면에서 쓰던 것을 그대로 쓴다.
// (편집기 동작에 얽힌 주의사항이 그 컴포넌트 주석에 정리되어 있다)
import MarkdownEditor from '@admin/components/Simditor.vue'

// 서버(problem/serializers.py)와 같은 값이어야 한다
const MAX_CASES = 20
const MAX_SAMPLES = 3
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
  hint: '', difficulty: 'L1', tags: []
})
const cases = ref([newCase()])

watch([form, cases], () => {
  if (watching) dirty.value = true
}, { deep: true })

function newCase () {
  return { input: '', output: '', is_sample: true }
}

function addCase () {
  casesTouched.value = true
  cases.value.push({ input: '', output: '', is_sample: false })
}

function goList () {
  router.push({ name: 'teacher-problem-list' })
}

function validate () {
  if (!form.title.trim()) return '제목을 입력해주세요'
  if (!form.description.trim()) return '문제 설명을 입력해주세요'
  if (!form.tags.length) return '태그를 하나 이상 골라주세요'
  const filled = cases.value.filter(c => c.input.trim() || c.output.trim())
  if (!filled.length) return '테스트 케이스를 하나 이상 넣어주세요'
  if (!filled.some(c => c.is_sample)) return '예제로 보여줄 케이스를 하나 이상 골라주세요'
  const samples = filled.filter(c => c.is_sample)
  if (samples.length > MAX_SAMPLES) return `예제는 ${MAX_SAMPLES}개까지 고를 수 있습니다`
  return null
}

function save () {
  const error = validate()
  if (error) {
    ElMessage.error(error)
    return
  }
  const data = { ...form, hint: form.hint || '' }
  // 편집 화면에서 케이스를 손대지 않았으면 보내지 않는다(서버가 기존 것을 유지한다)
  if (!isEdit.value || casesTouched.value) {
    data.cases = cases.value
      .filter(c => c.input.trim() || c.output.trim())
      .map(c => ({ input: c.input, output: c.output, is_sample: c.is_sample }))
  }

  saving.value = true
  const request = isEdit.value
    ? api.editProblem({ ...data, id: Number(problemId) })
    : api.createProblem(data)
  request.then(() => {
    saving.value = false
    dirty.value = false
    ElMessage.success(isEdit.value ? '수정했습니다' : '문제를 만들었습니다')
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
      hint: p.hint || '', difficulty: p.difficulty, tags: p.tags
    })
    // 저장된 예제만 되살린다. 채점용 케이스의 내용은 서버에 파일로만 있어
    // 화면으로 불러오지 않는다(크기가 클 수 있다).
    cases.value = (p.samples || []).map(s => ({ ...s, is_sample: true }))
    if (!cases.value.length) cases.value = [newCase()]
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
</style>
