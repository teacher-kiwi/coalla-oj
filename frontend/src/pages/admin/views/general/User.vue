<template>
  <div class="view">
    <Panel title="사용자">
      <template #header>
        <el-row :gutter="20">
          <el-col :span="8">
            <el-button v-show="selectedUsers.length" type="warning" :icon="Delete"
                       @click="deleteUsers(selectedUserIDs)">삭제</el-button>
          </el-col>
          <el-col :span="selectedUsers.length ? 16 : 24">
            <el-input v-model="keyword" :prefix-icon="SearchIcon" placeholder="검색어" />
          </el-col>
        </el-row>
      </template>
      <el-table v-loading="loadingTable" @selection-change="handleSelectionChange" :data="userList" class="full-width">
        <el-table-column type="selection" width="55" />
        <el-table-column prop="id" label="ID" />
        <el-table-column prop="username" label="사용자명" />
        <el-table-column prop="create_time" label="생성 일시">
          <template #default="{ row }">{{ localtime(row.create_time) }}</template>
        </el-table-column>
        <el-table-column prop="last_login" label="마지막 로그인">
          <template #default="{ row }">{{ localtime(row.last_login) }}</template>
        </el-table-column>
        <el-table-column prop="email" label="이메일" />
        <el-table-column prop="admin_type" label="사용자 유형">
          <template #default="{ row }">{{ USER_TYPE_LABEL[row.admin_type] || row.admin_type }}</template>
        </el-table-column>
        <el-table-column fixed="right" label="옵션" width="200">
          <template #default="{ row }">
            <icon-btn name="수정" icon="Edit" @click="openUserDialog(row.id)" />
            <icon-btn v-if="row.admin_type === 'Teacher'" name="교육 데이터 정리"
                      icon="Delete" @click="openTeacherCleanup(row)" />
            <icon-btn name="삭제" icon="Delete" @click="deleteUsers([row.id])" />
          </template>
        </el-table-column>
      </el-table>
      <div class="panel-options">
        <el-pagination class="page" layout="prev, pager, next"
                       @current-change="currentChange" :page-size="pageSize" :total="total" />
      </div>
    </Panel>

    <Panel>
      <template #title>
        사용자 가져오기
        <el-popover placement="right" trigger="hover">
          <template #reference><el-icon class="help-icon"><QuestionFilled /></el-icon></template>
          <p>헤더 없는 csv 파일만 지원합니다</p>
        </el-popover>
      </template>
      <el-upload v-if="!uploadUsers.length" action="" :show-file-list="false" accept=".csv" :before-upload="handleUsersCSV">
        <el-button size="small" type="primary" :icon="Upload">파일 선택</el-button>
      </el-upload>
      <template v-else>
        <el-table :data="uploadUsersPage">
          <el-table-column label="사용자명"><template #default="{ row }">{{ row[0] }}</template></el-table-column>
          <el-table-column label="비밀번호"><template #default="{ row }">{{ row[1] }}</template></el-table-column>
          <el-table-column label="이메일"><template #default="{ row }">{{ row[2] }}</template></el-table-column>
        </el-table>
        <div class="panel-options">
          <el-button type="primary" size="small" :icon="Upload" @click="handleUsersUpload">전체 가져오기</el-button>
          <el-button type="warning" size="small" @click="handleResetData">데이터 초기화</el-button>
          <el-pagination class="page" layout="prev, pager, next" :page-size="uploadUsersPageSize"
                         v-model:current-page="uploadUsersCurrentPage" :total="uploadUsers.length" />
        </div>
      </template>
    </Panel>

    <Panel title="사용자 생성">
      <el-form :model="formGenerateUser" ref="formGenerateUserRef">
        <el-row justify="space-between">
          <el-col :span="4">
            <el-form-item label="접두사" prop="prefix">
              <el-input v-model="formGenerateUser.prefix" placeholder="접두사" />
            </el-form-item>
          </el-col>
          <el-col :span="4">
            <el-form-item label="접미사" prop="suffix">
              <el-input v-model="formGenerateUser.suffix" placeholder="접미사" />
            </el-form-item>
          </el-col>
          <el-col :span="4">
            <el-form-item label="시작 번호" prop="number_from" required>
              <el-input-number v-model="formGenerateUser.number_from" class="full-width" />
            </el-form-item>
          </el-col>
          <el-col :span="4">
            <el-form-item label="끝 번호" prop="number_to" required>
              <el-input-number v-model="formGenerateUser.number_to" class="full-width" />
            </el-form-item>
          </el-col>
          <el-col :span="4">
            <el-form-item label="비밀번호 길이" prop="password_length" required>
              <el-input v-model="formGenerateUser.password_length" placeholder="비밀번호 길이" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item>
          <el-button type="primary" @click="generateUser" :loading="loadingGenerate">생성 및 내보내기</el-button>
          <span class="userPreview" v-if="formGenerateUser.number_from && formGenerateUser.number_to &&
                                          formGenerateUser.number_from <= formGenerateUser.number_to">
            The usernames will be {{ formGenerateUser.prefix + formGenerateUser.number_from + formGenerateUser.suffix }},
            <span v-if="formGenerateUser.number_from + 1 < formGenerateUser.number_to">
              {{ formGenerateUser.prefix + (formGenerateUser.number_from + 1) + formGenerateUser.suffix + '...' }}
            </span>
            <span v-if="formGenerateUser.number_from + 1 <= formGenerateUser.number_to">
              {{ formGenerateUser.prefix + formGenerateUser.number_to + formGenerateUser.suffix }}
            </span>
          </span>
        </el-form-item>
      </el-form>
    </Panel>

    <el-dialog title="교육 데이터 정리" v-model="showCleanupDialog" width="520px"
               :close-on-click-modal="false">
      <el-alert type="error" :closable="false" show-icon>
        <p><b>{{ cleanup.username }}</b> 선생님의 다음 데이터를 삭제합니다.
          <b>되돌릴 수 없습니다.</b></p>
        <ul class="cleanup-list">
          <li>학급 {{ cleanup.class_count }}개</li>
          <li>학생 계정 {{ cleanup.student_count }}개</li>
          <li>학생 제출 기록 {{ cleanup.student_submission_count }}건</li>
          <li>문제집 {{ cleanup.problem_set_count }}개</li>
          <li>학급 문제 {{ cleanup.private_problem_count }}개</li>
        </ul>
        <p>공개 문제와 선생님 본인의 제출 기록은 남습니다.</p>
      </el-alert>
      <template #footer>
        <el-button @click="showCleanupDialog = false">취소</el-button>
        <el-button type="danger" :loading="loadingCleanup" @click="runTeacherCleanup">
          삭제
        </el-button>
      </template>
    </el-dialog>

    <el-dialog title="사용자" v-model="showUserDialog" :close-on-click-modal="false">
      <el-form :model="editingUser" label-width="120px" label-position="left">
        <el-row :gutter="20">
          <el-col :span="12"><el-form-item label="사용자명" required><el-input v-model="editingUser.username" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="이메일" required><el-input v-model="editingUser.email" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="새 비밀번호"><el-input v-model="editingUser.password" /></el-form-item></el-col>
          <el-col :span="12">
            <el-form-item label="사용자 유형">
              <el-select v-model="editingUser.admin_type">
                <el-option v-for="(label, value) in USER_TYPE_LABEL" :key="value"
                           :label="label" :value="value" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="문제 권한">
              <el-select v-model="editingUser.problem_permission" :disabled="editingUser.admin_type !== 'Admin'">
                <el-option v-for="(label, value) in PROBLEM_PERMISSION_LABEL" :key="value"
                           :label="label" :value="value" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
          </el-col>
          <el-col :span="8">
          </el-col>
          <el-col :span="8">
            <el-form-item label="비활성화"><el-switch v-model="editingUser.is_disabled" /></el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <cancel @click="showUserDialog = false" />
        <save @click="saveUser" />
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { ElMessageBox, ElMessage, ElNotification } from 'element-plus'
import { Delete, Search as SearchIcon, Upload, QuestionFilled } from '@element-plus/icons-vue'
import papa from 'papaparse'
import api from '../../api.js'
import utils from '@/utils/utils'
import time from '@/utils/time'
import { USER_TYPE_LABEL, PROBLEM_PERMISSION_LABEL } from '@/utils/constants'

const pageSize = 10
const total = ref(0)
const userList = ref([])
const uploadUsers = ref([])
const uploadUsersPage = ref([])
const uploadUsersCurrentPage = ref(1)
const uploadUsersPageSize = 15
const keyword = ref('')
const showUserDialog = ref(false)
const editingUser = ref({})
const loadingTable = ref(false)
const loadingGenerate = ref(false)
const showCleanupDialog = ref(false)
const loadingCleanup = ref(false)
const cleanup = ref({})
const cleanupUserId = ref(null)
const currentPage = ref(0)
const selectedUsers = ref([])
const formGenerateUserRef = ref(null)
const formGenerateUser = reactive({ prefix: '', suffix: '', number_from: 0, number_to: 0, password_length: 8 })

const selectedUserIDs = computed(() => selectedUsers.value.map(u => u.id))

function localtime (val) { return time.utcToLocal(val) }

function currentChange (page) { currentPage.value = page; getUserList(page) }

function saveUser () {
  api.editUser(editingUser.value).then(() => {
    getUserList(currentPage.value)
    showUserDialog.value = false
  }).catch(() => {})
}

function openUserDialog (id) {
  showUserDialog.value = true
  api.getUser(id).then(res => {
    editingUser.value = res.data.data
    editingUser.value.password = ''
  })
}

function getUserList (page) {
  loadingTable.value = true
  api.getUserList((page - 1) * pageSize, pageSize, keyword.value).then(res => {
    loadingTable.value = false
    total.value = res.data.data.total
    userList.value = res.data.data.results
  }, () => { loadingTable.value = false })
}

function deleteUsers (ids) {
  ElMessageBox.confirm('사용자를 삭제하시겠습니까? 관련 데이터도 함께 삭제됩니다.', '확인', { type: 'warning' }).then(() => {
    api.deleteUsers(ids.join(',')).then(() => getUserList(currentPage.value)).catch(() => getUserList(currentPage.value))
  }, () => {})
}

function handleSelectionChange (val) { selectedUsers.value = val }

// 교사를 지우거나 유형을 바꾸려면 딸린 교육 데이터를 먼저 비워야 한다.
// 되돌릴 수 없어서 무엇이 지워지는지 보여주고 확인받는다.
function openTeacherCleanup (row) {
  api.getTeacherData(row.id).then(res => {
    cleanup.value = res.data.data
    cleanupUserId.value = row.id
    showCleanupDialog.value = true
  }, () => {})
}

function runTeacherCleanup () {
  loadingCleanup.value = true
  api.purgeTeacherData(cleanupUserId.value).then(() => {
    loadingCleanup.value = false
    showCleanupDialog.value = false
    ElMessage.success('교육 데이터를 정리했습니다')
    getUserList(currentPage.value)
  }, () => {
    loadingCleanup.value = false
  })
}

function generateUser () {
  formGenerateUserRef.value.validate((valid) => {
    if (!valid) { ElMessage.error('입력값을 확인해주세요'); return }
    loadingGenerate.value = true
    api.generateUser({ ...formGenerateUser }).then(res => {
      loadingGenerate.value = false
      const url = '/admin/generate_user?file_id=' + res.data.data.file_id
      utils.downloadFile(url).then(() => {
        ElMessageBox.alert('사용자 생성이 완료되었습니다. 사용자 목록 파일이 다운로드되었습니다.', '알림')
      })
      getUserList(1)
    }).catch(() => { loadingGenerate.value = false })
  })
}

function handleUsersCSV (file) {
  papa.parse(file, {
    complete: (results) => {
      const data = results.data.filter(user => user[0] && user[1] && user[2])
      const delta = results.data.length - data.length
      if (delta > 0) ElNotification.warning({ title: '경고', message: delta + '명이 빈 값으로 인해 제외되었습니다' })
      uploadUsersCurrentPage.value = 1
      uploadUsers.value = data
      uploadUsersPage.value = data.slice(0, uploadUsersPageSize)
    },
    error: (error) => { ElMessage.error(String(error)) }
  })
  return false
}

function handleUsersUpload () {
  api.importUsers(uploadUsers.value).then(() => { getUserList(1); handleResetData() }).catch(() => {})
}

function handleResetData () { uploadUsers.value = [] }

onMounted(() => { getUserList(1) })

watch(keyword, () => { currentChange(1) })

watch(() => editingUser.value.admin_type, (val) => {
  if (val === 'Super Admin') editingUser.value.problem_permission = 'All'
  else if (val === 'Regular User') editingUser.value.problem_permission = 'None'
})

watch(uploadUsersCurrentPage, (page) => {
  uploadUsersPage.value = uploadUsers.value.slice((page - 1) * uploadUsersPageSize, page * uploadUsersPageSize)
})
</script>

<style scoped lang="less">
  .userPreview { padding-left: 10px; }
  .full-width { width: 100%; }
  .help-icon { margin-left: 4px; }

.cleanup-list {
  // 들여쓰기는 padding 으로 적는다. margin 으로만 주면 목록 기본값인
  // 왼쪽 padding 40px 이 그 아래 그대로 깔려 실제로는 58px 이 된다.
  margin: 8px 0;
  padding-left: 18px;
  line-height: 1.7;
}
</style>
