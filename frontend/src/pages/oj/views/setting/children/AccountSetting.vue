<template>
  <div class="setting-main">
    <div class="flex-container">
      <div class="left">
        <p class="section-title">비밀번호 변경</p>
        <el-form class="setting-content" ref="formPasswordRef" :model="formPassword" :rules="rulePassword" label-width="160px">
          <el-form-item label="기존 비밀번호" prop="old_password">
            <el-input v-model="formPassword.old_password" type="password" />
          </el-form-item>
          <el-form-item label="새 비밀번호" prop="new_password">
            <el-input v-model="formPassword.new_password" type="password" />
          </el-form-item>
          <el-form-item label="새 비밀번호 확인" prop="again_password">
            <el-input v-model="formPassword.again_password" type="password" />
          </el-form-item>
          <el-form-item v-if="visible.passwordAlert">
            <el-alert type="success" :closable="false">잠시 후 자동으로 로그아웃됩니다. 새 비밀번호로 다시 로그인해주세요.</el-alert>
          </el-form-item>
          <el-button type="primary" :loading="loading.btnPassword" @click="changePassword">비밀번호 업데이트</el-button>
        </el-form>
      </div>

      <div class="middle separator" />

      <div class="right">
        <p class="section-title">이메일 변경</p>
        <el-form class="setting-content" ref="formEmailRef" :model="formEmail" :rules="ruleEmail" label-width="160px">
          <el-form-item label="현재 비밀번호" prop="password">
            <el-input v-model="formEmail.password" type="password" />
          </el-form-item>
          <el-form-item label="기존 이메일">
            <el-input v-model="formEmail.old_email" disabled />
          </el-form-item>
          <el-form-item label="새 이메일" prop="new_email">
            <el-input v-model="formEmail.new_email" />
          </el-form-item>
          <el-button type="primary" :loading="loading.btnEmail" @click="changeEmail">이메일 변경</el-button>
        </el-form>
      </div>
    </div>

    <!-- 구글로 가입한 사용자만 스스로 탈퇴할 수 있다.
         관리자와 수업용 학생 계정은 서버에서도 막는다. -->
    <div v-if="canDelete" class="danger-zone">
      <p class="section-title danger">회원 탈퇴</p>
      <p class="danger-desc">
        탈퇴하면 계정과 제출 기록이 모두 삭제되며 되돌릴 수 없습니다.
      </p>
      <el-button type="danger" plain @click="openDelete">회원 탈퇴</el-button>
    </div>

    <el-dialog v-model="deleteVisible" title="정말 탈퇴하시겠습니까?" width="460px"
               :close-on-click-modal="false">
      <el-alert type="error" :closable="false" show-icon>
        <p>다음 정보가 <b>모두 삭제되며 되돌릴 수 없습니다.</b></p>
        <ul class="delete-list">
          <li>내 계정과 프로필</li>
          <li>내가 제출한 코드 {{ deleteInfo.submission_count }}건</li>
          <li v-if="deleteInfo.class_count">
            내가 만든 학급 {{ deleteInfo.class_count }}개와
            <b>학생 계정 {{ deleteInfo.student_count }}개</b>
          </li>
          <li v-if="deleteInfo.class_count">학생들이 제출한 코드 전부</li>
        </ul>
      </el-alert>
      <p class="reauth-guide">본인 확인을 위해 구글로 다시 로그인해주세요.</p>
      <div ref="googleBtnRef" class="google-btn" />
      <p v-if="!googleReady" class="reauth-guide">구글 로그인을 불러오지 못했습니다.</p>
      <template #footer>
        <el-button @click="deleteVisible = false">취소</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@oj/api'
import { useForm } from '@oj/components/mixins'
import { useUserStore } from '@/store/user'
import { useAppStore } from '@/store/app'
import { renderGoogleButton } from '@/utils/google'
const router = useRouter()
const userStore = useUserStore()
const appStore = useAppStore()
const { validateForm } = useForm()

const formPasswordRef = ref(null)
const formEmailRef = ref(null)

const loading = reactive({ btnPassword: false, btnEmail: false })
const deleteVisible = ref(false)
const deleteInfo = ref({ class_count: 0, student_count: 0, submission_count: 0 })
const googleBtnRef = ref(null)
const googleReady = ref(true)
// 구글로 가입한 일반 사용자(교사·개인 학생)만 스스로 탈퇴할 수 있다
const canDelete = computed(() => !!userStore.user.is_google_account && !userStore.isAdminRole)
const visible = reactive({ passwordAlert: false, emailAlert: false })

const formPassword = ref({ old_password: '', new_password: '', again_password: '' })
const formEmail = ref({ password: '', old_email: '', new_email: '' })

const CheckAgainPassword = (rule, value, callback) => {
  if (value !== formPassword.value.new_password) callback(new Error('password does not match'))
  else callback()
}
const CheckNewPassword = (rule, value, callback) => {
  if (formPassword.value.old_password !== '' && formPassword.value.old_password === formPassword.value.new_password) {
    callback(new Error("The new password doesn't change"))
  } else {
    formPasswordRef.value?.validateField('again_password')
    callback()
  }
}

const oldPasswordCheck = [{ required: true, trigger: 'blur', min: 6, max: 20 }]

const rulePassword = {
  old_password: oldPasswordCheck,
  new_password: [
    { required: true, trigger: 'blur', min: 6, max: 20 },
    { validator: CheckNewPassword, trigger: 'blur' }
  ],
  again_password: [
    { required: true, validator: CheckAgainPassword, trigger: 'change' }
  ]
}

const ruleEmail = {
  password: oldPasswordCheck,
  new_email: [{ required: true, type: 'email', trigger: 'change' }]
}

async function changePassword () {
  const valid = await validateForm(formPasswordRef.value)
  if (!valid) return
  loading.btnPassword = true
  const data = { ...formPassword.value }
  delete data.again_password
  try {
    await api.changePassword(data)
    loading.btnPassword = false
    visible.passwordAlert = true
    ElMessage.success('비밀번호를 변경했습니다')
    setTimeout(() => {
      visible.passwordAlert = false
      router.push({ name: 'logout' })
    }, 5000)
  } catch (res) {
    loading.btnPassword = false
  }
}

async function changeEmail () {
  const valid = await validateForm(formEmailRef.value)
  if (!valid) return
  loading.btnEmail = true
  const data = { ...formEmail.value }
  try {
    await api.changeEmail(data)
    loading.btnEmail = false
    visible.emailAlert = true
    ElMessage.success('이메일을 변경했습니다')
    formEmailRef.value?.resetFields()
  } catch (res) {
    loading.btnEmail = false
  }
}

async function openDelete () {
  try {
    const resp = await api.getAccountDeleteInfo()
    deleteInfo.value = resp.data.data
  } catch (e) {
    return
  }
  deleteVisible.value = true
  await nextTick()
  googleReady.value = await renderGoogleButton(
    googleBtnRef.value, appStore.website.google_client_id, confirmDelete)
}

async function confirmDelete (credential) {
  try {
    await ElMessageBox.confirm('마지막 확인입니다. 정말 탈퇴하시겠습니까?', '회원 탈퇴',
      { confirmButtonText: '탈퇴', cancelButtonText: '취소', type: 'error' })
  } catch (e) {
    return
  }
  try {
    await api.deleteAccount(credential)
  } catch (e) {
    return
  }
  deleteVisible.value = false
  userStore.clearProfile()
  ElMessage.success('탈퇴가 완료되었습니다')
  router.push({ name: 'home' })
}

onMounted(() => {
  formEmail.value.old_email = userStore.user.email || ''
})
</script>

<style lang="less" scoped>
  .danger-zone {
    margin-top: 30px;
    padding-top: 20px;
    border-top: 1px solid #ebeef5;
  }

  .section-title.danger {
    color: #f56c6c;
  }

  .danger-desc {
    font-size: 13px;
    color: #909399;
    line-height: 1.7;
    margin-bottom: 12px;
  }

  .delete-list {
    margin: 8px 0 0 16px;
    line-height: 1.8;
  }

  .reauth-guide {
    font-size: 13px;
    color: #606266;
    margin-top: 16px;
  }

  .google-btn {
    display: flex;
    justify-content: center;
    padding: 10px 0;
  }

  .flex-container {
    display: flex;
    justify-content: flex-start;
    .left {
      flex: 1 0;
      width: 250px;
      padding-right: 5%;
    }
    > .middle {
      flex: none;
    }
    .right {
      flex: 1 0;
      width: 250px;
    }
  }
</style>
