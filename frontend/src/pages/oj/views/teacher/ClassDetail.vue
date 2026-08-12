<template>
  <Panel shadow>
    <template #title>
      <span v-if="info.id">{{ info.school_name }} {{ info.grade }}학년 {{ info.class_no }}반</span>
      <span v-else>학급</span>
    </template>
    <template #extra>
      <el-button @click="goList">목록</el-button>
      <el-button type="primary" :icon="Plus" @click="dialogVisible = true">학생 계정 만들기</el-button>
    </template>

    <el-alert v-if="issued.length" type="success" show-icon :closable="false" class="issued">
      <p>학생 계정 {{ issued.length }}개를 만들었습니다. <b>비밀번호는 지금만 확인할 수 있습니다.</b></p>
      <el-button type="primary" size="small" @click="downloadSheet">엑셀로 내려받기</el-button>
      <el-table :data="issued" size="small" class="issued-table">
        <el-table-column label="번호" prop="number" width="80" />
        <el-table-column label="비밀번호" prop="password" />
      </el-table>
    </el-alert>

    <el-table v-loading="loading" :data="students" class="full-width">
      <el-table-column label="번호" prop="number" width="80" />
      <el-table-column label="마지막 로그인">
        <template #default="{ row }">{{ row.last_login ? localtime(row.last_login) : '접속 기록 없음' }}</template>
      </el-table-column>
      <el-table-column label="관리" width="240">
        <template #default="{ row }">
          <el-button size="small" @click="resetPassword(row)">비밀번호 초기화</el-button>
          <el-button size="small" type="danger" @click="removeStudent(row)">삭제</el-button>
        </template>
      </el-table-column>
    </el-table>

    <p v-if="!loading && !students.length" class="empty">
      아직 학생 계정이 없습니다. "학생 계정 만들기"로 번호 범위를 지정해 한 번에 만드세요.
    </p>

    <el-dialog v-model="dialogVisible" title="학생 계정 만들기" width="420px" :close-on-click-modal="false">
      <el-form label-width="100px">
        <el-form-item label="시작 번호">
          <el-input-number v-model="form.number_from" :min="1" :max="99" />
        </el-form-item>
        <el-form-item label="끝 번호">
          <el-input-number v-model="form.number_to" :min="1" :max="99" />
        </el-form-item>
      </el-form>
      <p class="field-help">
        번호마다 계정이 하나씩 만들어지고, 숫자 4자리 비밀번호가 자동으로 발급됩니다.
        학생은 학교·학년·반을 검색해 자기 번호와 비밀번호로 로그인합니다.
      </p>
      <template #footer>
        <el-button @click="dialogVisible = false">취소</el-button>
        <el-button type="primary" :loading="saving" @click="submit">만들기</el-button>
      </template>
    </el-dialog>
  </Panel>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '@oj/api'
import time from '@/utils/time'

const route = useRoute()
const router = useRouter()
const classId = route.params.classId

const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const info = ref({})
const students = ref([])
// 발급 직후에만 보여준다. 해시로 저장되므로 다시 조회할 수 없다.
const issued = ref([])
let sheetFileId = null

const form = reactive({ number_from: 1, number_to: 20 })

function goList () {
  router.push({ name: 'teacher-class-list' })
}

function localtime (val) {
  return time.utcToLocal(val)
}

function load () {
  loading.value = true
  api.getClass(classId).then(res => { info.value = res.data.data }, () => {})
  api.getClassStudents(classId).then(res => {
    loading.value = false
    students.value = res.data.data
  }, () => {
    loading.value = false
  })
}

function submit () {
  if (form.number_from > form.number_to) {
    ElMessage.error('시작 번호는 끝 번호보다 작아야 합니다')
    return
  }
  saving.value = true
  api.createStudents({
    school_class: parseInt(classId),
    number_from: form.number_from,
    number_to: form.number_to
  }).then(res => {
    saving.value = false
    dialogVisible.value = false
    sheetFileId = res.data.data.file_id
    issued.value = res.data.data.students
    load()
  }, () => {
    saving.value = false
  })
}

function downloadSheet () {
  if (!sheetFileId) return
  window.open(`/api/teacher/student/sheet?file_id=${sheetFileId}`)
}

function resetPassword (row) {
  ElMessageBox.confirm(`${row.number}번 학생의 비밀번호를 새로 발급합니다.`, '비밀번호 초기화', {
    confirmButtonText: '초기화', cancelButtonText: '취소'
  }).then(() => {
    api.resetStudentPassword(row.id).then(res => {
      const data = res.data.data
      ElMessageBox.alert(
        `${data.number}번 학생의 새 비밀번호는 ${data.password} 입니다.\n학생에게 알려주세요.`,
        '초기화 완료')
      load()
    }).catch(() => {})
  }).catch(() => {})
}

function removeStudent (row) {
  ElMessageBox.confirm(
    `${row.number}번 학생 계정을 삭제합니다. 제출한 기록도 함께 사라지며 되돌릴 수 없습니다.`,
    '학생 삭제', { confirmButtonText: '삭제', cancelButtonText: '취소', type: 'warning' }
  ).then(() => {
    api.deleteStudent(row.id).then(() => {
      ElMessage.success('삭제했습니다')
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

.issued {
  margin-bottom: 20px;
}

.issued-table {
  margin-top: 10px;
  max-width: 320px;
}

.field-help {
  font-size: 12px;
  color: #909399;
  line-height: 1.6;
}

.empty {
  text-align: center;
  color: #909399;
  padding: 30px 0;
}
</style>
