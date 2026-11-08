<template>
  <div>
    <Panel shadow>
      <template #title>바로 과제 만들기</template>

      <el-alert type="info" show-icon :closable="false" class="panel-guide">
        만들면 바로 시작되고 6자리 코드가 나옵니다. 학생은 계정 없이 코드로 들어와
        번호·닉네임·4자리 숫자만 정하고 풉니다. 문제와 언어는 만든 뒤에 바꿀 수 없습니다.
      </el-alert>

      <el-form label-width="90px" class="form">
        <el-form-item label="제목" required>
          <el-input v-model="form.title" maxlength="128"
                    placeholder="예: 3학년 2반 반복문 연습 (학년·반이 필요하면 여기에)" />
        </el-form-item>

        <el-form-item label="마감 시각" required>
          <div class="deadline">
            <el-date-picker v-model="form.endTime" type="datetime" format="YYYY-MM-DD HH:mm"
                            :clearable="false" :disabled-date="isPast" />
            <span class="quick">
              <el-button size="small" @click="setDeadline(40)">40분 뒤</el-button>
              <el-button size="small" @click="setDeadline(60)">1시간 뒤</el-button>
              <el-button size="small" @click="setDeadline(60 * 24)">내일 이 시각</el-button>
            </span>
          </div>
        </el-form-item>

        <el-form-item label="언어" required>
          <el-checkbox-group v-model="form.languages">
            <el-checkbox v-for="lang in languageOptions" :key="lang" :value="lang">
              {{ lang === 'Block Coding' ? '블록 코딩' : lang }}
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>

        <el-form-item label="문제" required>
          <div class="problems">
            <el-table :data="picked" class="full-width" size="small">
              <el-table-column label="순서" width="60">
                <template #default="{ $index }">{{ $index + 1 }}</template>
              </el-table-column>
              <el-table-column label="#" prop="display_id" width="80" />
              <el-table-column label="제목" prop="title" min-width="160" />
              <el-table-column label="관리" width="210">
                <template #default="{ $index }">
                  <el-button size="small" :disabled="$index === 0" @click="move($index, -1)">위로</el-button>
                  <el-button size="small" :disabled="$index === picked.length - 1"
                             @click="move($index, 1)">아래로</el-button>
                  <el-button size="small" type="danger" @click="picked.splice($index, 1)">빼기</el-button>
                </template>
              </el-table-column>
              <template #empty>"문제 추가"로 문제를 고르세요</template>
            </el-table>
            <el-button :icon="Plus" class="add-problem" @click="openPicker">문제 추가</el-button>
          </div>
        </el-form-item>
      </el-form>

      <div class="submit">
        <el-button type="primary" size="large" :loading="saving" @click="create">만들기</el-button>
      </div>
    </Panel>

    <el-dialog v-model="pickerVisible" title="문제 추가" width="720px" :close-on-click-modal="false">
      <div class="picker-filter">
        <el-input v-model="keyword" placeholder="문제 제목이나 번호로 검색 (Enter)"
                  clearable @keyup.enter="search(1)" />
        <el-select v-model="difficulty" placeholder="난이도" clearable class="picker-difficulty"
                   @change="search(1)">
          <el-option v-for="d in DIFFICULTY" :key="d.value" :value="d.value" :label="d.label" />
        </el-select>
        <span class="picker-switch">
          <span class="picker-switch-label">즐겨찾기</span>
          <el-switch v-model="favoriteOnly" @change="search(1)" />
        </span>
      </div>
      <el-table v-loading="searching" :data="candidates" class="full-width"
                @selection-change="rows => { selected = rows }">
        <el-table-column type="selection" width="45" :selectable="row => !pickedIds.has(row.id)" />
        <el-table-column label="#" prop="display_id" width="100" />
        <el-table-column label="제목">
          <template #default="{ row }">
            {{ row.title }}
            <span v-if="pickedIds.has(row.id)" class="already-in">담겨 있음</span>
          </template>
        </el-table-column>
        <el-table-column label="난이도" width="90">
          <template #default="{ row }"><DifficultyTag :value="row.difficulty" /></template>
        </el-table-column>
        <el-table-column label="범위" width="90" align="center">
          <template #default="{ row }"><ScopeTag :value="row.visibility" /></template>
        </el-table-column>
      </el-table>
      <p class="picker-guide">
        내가 만든 학급 문제도 담을 수 있습니다. 과제에 들어온 학생은 그 과제 안에서만 볼 수 있습니다.
      </p>
      <Pagination :total="candidateTotal" :page-size="10" :current="candidatePage" @on-change="search" />
      <template #footer>
        <el-button @click="pickerVisible = false">취소</el-button>
        <el-button type="primary" @click="addPicked">
          {{ selected.length ? `${selected.length}개 추가` : '추가' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '@oj/api'
import DifficultyTag from '@oj/components/DifficultyTag.vue'
import ScopeTag from '@oj/components/ScopeTag.vue'
import Pagination from '@oj/components/Pagination.vue'
import { DIFFICULTY } from '@/utils/constants'

const router = useRouter()

function minutesFromNow (minutes) {
  // 분 단위로 맞춰 둔다. 초가 붙어 있으면 "14:59:37 마감" 처럼 어색하다.
  const date = new Date(Date.now() + minutes * 60 * 1000)
  date.setSeconds(0, 0)
  return date
}

const form = reactive({ title: '', endTime: minutesFromNow(60), languages: [] })
const languageOptions = ref([])
const picked = ref([])
const pickedIds = computed(() => new Set(picked.value.map(p => p.id)))
const saving = ref(false)

function isPast (date) {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return date < today
}

function setDeadline (minutes) {
  form.endTime = minutesFromNow(minutes)
}

function move (index, delta) {
  const list = picked.value
  ;[list[index], list[index + delta]] = [list[index + delta], list[index]]
}

function create () {
  if (!form.title.trim()) return ElMessage.error('제목을 입력하세요')
  if (!picked.value.length) return ElMessage.error('문제를 하나 이상 고르세요')
  if (!form.languages.length) return ElMessage.error('언어를 하나 이상 고르세요')
  if (form.endTime <= new Date()) return ElMessage.error('마감 시각은 지금보다 뒤여야 합니다')
  saving.value = true
  api.createHomework({
    title: form.title.trim(),
    problems: picked.value.map(p => p.id),
    languages: form.languages,
    end_time: form.endTime.toISOString()
  }).then(res => {
    // 현황판에서 코드를 크게 띄워 바로 학생들에게 보여 준다
    router.push({ name: 'teacher-homework-board', params: { id: res.data.data.id },
                  query: { created: 1 } })
  }, () => {}).finally(() => { saving.value = false })
}

// ---- 문제 고르기 (문제집의 "문제 추가"와 같은 기준) ----
const pickerVisible = ref(false)
const searching = ref(false)
const keyword = ref('')
const difficulty = ref('')
const favoriteOnly = ref(false)
const candidates = ref([])
const candidateTotal = ref(0)
const candidatePage = ref(1)
const selected = ref([])

function openPicker () {
  selected.value = []
  pickerVisible.value = true
  search(1)
}

function search (page) {
  candidatePage.value = page
  searching.value = true
  const params = {
    keyword: keyword.value,
    difficulty: difficulty.value,
    favorite: favoriteOnly.value ? '1' : '',
    mine: 1
  }
  api.getProblemList((page - 1) * 10, 10, params).then(res => {
    candidates.value = res.data.data.results
    candidateTotal.value = res.data.data.total
  }, () => {}).finally(() => { searching.value = false })
}

function addPicked () {
  picked.value.push(...selected.value.filter(p => !pickedIds.value.has(p.id)))
  pickerVisible.value = false
}

onMounted(() => {
  // 기본은 쓸 수 있는 언어 전부. 블록 코딩을 맨 앞에 둔다.
  api.getLanguages().then(res => {
    const names = (res.data.data.languages || []).map(lang => lang.name)
    languageOptions.value = ['Block Coding', ...names]
    form.languages = [...languageOptions.value]
  }, () => {})
})
</script>

<style lang="less" scoped>
.form {
  margin-top: 16px;
}
.deadline {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.problems {
  width: 100%;
  .add-problem {
    margin-top: 8px;
  }
}
.submit {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}
.picker-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
  .el-input {
    flex: 1 1 200px;
  }
}
.picker-difficulty {
  width: 120px;
}
.picker-switch {
  display: flex;
  align-items: center;
  gap: 6px;
}
.picker-guide {
  font-size: 13px;
  color: #909399;
}
.already-in {
  margin-left: 6px;
  font-size: 12px;
  color: #909399;
}
</style>
