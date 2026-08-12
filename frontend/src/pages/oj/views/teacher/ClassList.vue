<template>
  <Panel shadow>
    <template #title>내 학급</template>
    <template #extra>
      <el-button type="primary" :icon="Plus" @click="openDialog">학급 만들기</el-button>
    </template>

    <el-table v-loading="loading" :data="classes" class="full-width">
      <el-table-column label="학교" prop="school_name" />
      <el-table-column label="학급">
        <template #default="{ row }">{{ row.grade }}학년 {{ row.class_no }}반</template>
      </el-table-column>
      <el-table-column label="학년도" prop="year" width="100" />
      <el-table-column label="학생 수" prop="student_count" width="100" />
      <el-table-column label="관리" width="220">
        <template #default="{ row }">
          <el-button size="small" type="primary" @click="goDetail(row.id)">학생 관리</el-button>
          <el-button size="small" @click="archive(row)">학년 종료</el-button>
        </template>
      </el-table-column>
    </el-table>

    <p v-if="!loading && !classes.length" class="empty">
      아직 만든 학급이 없습니다. "학급 만들기"로 시작하세요.
    </p>

    <el-dialog v-model="dialogVisible" title="학급 만들기" width="460px" :close-on-click-modal="false">
      <el-form label-width="110px">
        <el-form-item label="학교" required>
          <div class="school-search">
            <el-input ref="schoolInputRef" v-model="schoolKeyword" clearable
                      placeholder="학교 이름을 두 글자 이상 입력하세요"
                      @clear="clearSchool" />
            <ul v-if="suggestions.length" class="school-list">
              <li v-for="item in suggestions" :key="item.id" @click="selectSchool(item)">
                <span>{{ item.name }}</span>
                <span class="school-office">{{ item.office }}</span>
              </li>
            </ul>
            <div v-if="form.school" class="field-help">선택됨: {{ schoolKeyword }}</div>
            <div v-else-if="searched && !suggestions.length" class="field-help">
              검색된 학교가 없습니다.
            </div>
            <div v-else class="field-help">목록에서 학교를 선택해야 합니다.</div>
          </div>
        </el-form-item>
        <el-form-item label="학년도" required>
          <el-input-number v-model="form.year" :min="2000" :max="2100" />
        </el-form-item>
        <el-form-item label="학년" required>
          <el-input-number v-model="form.grade" :min="1" :max="6" />
        </el-form-item>
        <el-form-item label="반" required>
          <el-input-number v-model="form.class_no" :min="1" :max="99" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">취소</el-button>
        <el-button type="primary" :loading="saving" @click="submit">만들기</el-button>
      </template>
    </el-dialog>
  </Panel>
</template>

<script setup>
import { ref, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '@oj/api'

const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const classes = ref([])
const schoolKeyword = ref('')
const schoolInputRef = ref(null)
const suggestions = ref([])
const searched = ref(false)

const form = ref({})

function defaultForm () {
  return {
    school: null,
    year: new Date().getFullYear(),
    grade: 3,
    class_no: 1
  }
}

function load () {
  loading.value = true
  api.getMyClasses().then(res => {
    loading.value = false
    classes.value = res.data.data
  }, () => {
    loading.value = false
  })
}

function openDialog () {
  form.value = defaultForm()
  schoolKeyword.value = ''
  selectedName = ''
  suggestions.value = []
  searched.value = false
  dialogVisible.value = true
}

// 한글은 IME 조합을 거치는데, el-input 은 조합 중 입력을 무시한다
// (`if (isComposing.value) return`). 그래서 v-model 만 보면 마지막 글자가
// 반영되지 않아 검색이 한 글자 뒤처진다.
// 네이티브 input 이벤트는 조합 중에도 발생하므로 그쪽을 직접 듣는다.
let searchTimer = null
let nativeInput = null

function onNativeInput (event) {
  const keyword = event.target.value
  schoolKeyword.value = keyword
  if (keyword !== selectedName) form.value.school = null

  clearTimeout(searchTimer)
  if (keyword.trim().length < 2) {
    suggestions.value = []
    searched.value = false
    return
  }
  searchTimer = setTimeout(() => searchSchools(keyword.trim()), 250)
}

function searchSchools (keyword) {
  api.searchSchool(keyword).then(res => {
    suggestions.value = res.data.data.results
    searched.value = true
  }, () => {
    suggestions.value = []
  })
}

let selectedName = ''

function selectSchool (item) {
  selectedName = item.name
  schoolKeyword.value = item.name
  form.value.school = item.id
  suggestions.value = []
}

// 지우기(x) 버튼은 네이티브 input 이벤트를 발생시키지 않으므로 따로 받는다.
function clearSchool () {
  form.value.school = null
  suggestions.value = []
  searched.value = false
}

watch(dialogVisible, async (open) => {
  if (!open) {
    nativeInput?.removeEventListener('input', onNativeInput)
    nativeInput = null
    return
  }
  await nextTick()
  nativeInput = schoolInputRef.value?.input
  nativeInput?.addEventListener('input', onNativeInput)
})

function submit () {
  if (!form.value.school) {
    ElMessage.error('학교를 선택해주세요')
    return
  }
  saving.value = true
  api.createClass(form.value).then(() => {
    saving.value = false
    dialogVisible.value = false
    ElMessage.success('학급을 만들었습니다')
    load()
  }, () => {
    saving.value = false
  })
}

function goDetail (id) {
  router.push({ name: 'teacher-class-detail', params: { classId: id } })
}

function archive (row) {
  ElMessageBox.confirm(
    `${row.school_name} ${row.grade}학년 ${row.class_no}반을 학년 종료 처리합니다.\n` +
    '목록에서 숨겨지며 학생은 로그인할 수 없게 됩니다. 계정과 기록은 남습니다.',
    '학년 종료', { confirmButtonText: '종료', cancelButtonText: '취소', type: 'warning' }
  ).then(() => {
    api.editClass({ id: row.id, is_archived: true }).then(() => {
      ElMessage.success('학년 종료 처리했습니다')
      load()
    }).catch(() => {})
  }).catch(() => {})
}

onMounted(load)
onBeforeUnmount(() => {
  clearTimeout(searchTimer)
  nativeInput?.removeEventListener('input', onNativeInput)
})
</script>

<style scoped>
.full-width {
  width: 100%;
}

.school-search {
  width: 100%;
}

.school-list {
  list-style: none;
  margin: 4px 0 0;
  padding: 0;
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
}

.school-list li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  cursor: pointer;
  line-height: 1.4;
}

.school-list li:hover {
  background-color: #f5f7fa;
}

.school-office {
  font-size: 12px;
  color: #909399;
}

.field-help {
  font-size: 12px;
  color: #909399;
  line-height: 1.6;
  margin-top: 4px;
}

.empty {
  text-align: center;
  color: #909399;
  padding: 30px 0;
}
</style>
