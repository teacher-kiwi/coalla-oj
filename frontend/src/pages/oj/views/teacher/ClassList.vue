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
      <el-table-column label="아이디 접두사" prop="username_prefix" width="150" />
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
          <el-select v-model="form.school" filterable remote :remote-method="searchSchool"
                     :loading="schoolLoading" placeholder="학교 이름을 입력하세요" class="full-width">
            <el-option v-for="s in schools" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
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
        <el-form-item label="아이디 접두사" required>
          <el-input v-model="form.username_prefix" placeholder="예: kim3" />
          <div class="field-help">
            학생 계정 아이디에 쓰입니다(kim3-01, kim3-02 …).
            영문 소문자·숫자·하이픈 3~20자이며, 다른 선생님과 겹칠 수 없습니다.
            학생은 이 아이디를 직접 입력하지 않습니다.
          </div>
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
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '@oj/api'

const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const schoolLoading = ref(false)
const dialogVisible = ref(false)
const classes = ref([])
const schools = ref([])

const form = ref({})

function defaultForm () {
  return {
    school: null,
    year: new Date().getFullYear(),
    grade: 3,
    class_no: 1,
    username_prefix: ''
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
  schools.value = []
  dialogVisible.value = true
}

function searchSchool (keyword) {
  if (!keyword || keyword.trim().length < 2) return
  schoolLoading.value = true
  api.searchSchool(keyword.trim()).then(res => {
    schoolLoading.value = false
    schools.value = res.data.data.results
  }, () => {
    schoolLoading.value = false
  })
}

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
</script>

<style scoped>
.full-width {
  width: 100%;
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
