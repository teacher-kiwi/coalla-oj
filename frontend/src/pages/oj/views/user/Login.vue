<template>
  <div>
    <el-form ref="formRef" :model="formLogin" :rules="ruleLogin">
      <el-form-item prop="username">
        <el-input v-model="formLogin.username" placeholder="사용자명" size="large" :prefix-icon="User" @keyup.enter="handleLogin" />
      </el-form-item>
      <el-form-item prop="password">
        <el-input type="password" v-model="formLogin.password" placeholder="비밀번호" size="large" :prefix-icon="Lock" @keyup.enter="handleLogin" />
      </el-form-item>
    </el-form>
    <div class="footer">
      <el-button type="primary" class="btn" :loading="btnLoginLoading" @click="handleLogin">
        로그인
      </el-button>
      <a v-if="appStore.website.allow_register" @click.stop="handleBtnClick('register')">계정이 없으신가요? 지금 가입하세요!</a>
      <a @click.stop="goResetPassword" class="forget-link">비밀번호 찾기</a>
    </div>

    <template v-if="appStore.website.google_client_id">
      <el-divider class="divider">선생님이신가요?</el-divider>
      <el-alert v-if="pendingApproval" type="info" show-icon :closable="false" class="notice">
        가입 신청이 접수되었습니다. 관리자 승인 후 이용할 수 있습니다.
      </el-alert>
      <div v-show="!pendingApproval" ref="googleBtnRef" class="google-btn" />
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import api from '@oj/api'
import { useForm } from '@oj/components/mixins'
import { useAppStore } from '@/store/app'
import { useUserStore } from '@/store/user'
const router = useRouter()
const appStore = useAppStore()
const userStore = useUserStore()
const { validateForm } = useForm()

const googleBtnRef = ref(null)
const pendingApproval = ref(false)
const formRef = ref(null)
const btnLoginLoading = ref(false)
const formLogin = ref({ username: '', password: '' })

const ruleLogin = {
  username: [
    { required: true, trigger: 'blur' }
  ],
  password: [
    { required: true, trigger: 'change', min: 6, max: 20 }
  ]
}

// 구글 로그인 스크립트는 필요한 순간에만 불러온다.
const GSI_SRC = 'https://accounts.google.com/gsi/client'
let gsiScript = null

function loadGsi () {
  return new Promise((resolve, reject) => {
    if (window.google?.accounts?.id) return resolve()
    gsiScript = document.querySelector(`script[src="${GSI_SRC}"]`)
    if (!gsiScript) {
      gsiScript = document.createElement('script')
      gsiScript.src = GSI_SRC
      gsiScript.async = true
      gsiScript.defer = true
      document.head.appendChild(gsiScript)
    }
    gsiScript.addEventListener('load', resolve, { once: true })
    gsiScript.addEventListener('error', reject, { once: true })
  })
}

async function handleGoogleCredential (response) {
  try {
    const res = await api.googleLogin(response.credential)
    if (res.data.data?.status === 'pending') {
      pendingApproval.value = true
      return
    }
    appStore.changeModalStatus({ visible: false })
    userStore.getProfile()
    ElMessage.success('환영합니다')
  } catch (e) {
    // 에러 메시지는 api 인터셉터가 표시한다
  }
}

async function initGoogleButton () {
  const clientId = appStore.website.google_client_id
  if (!clientId || !googleBtnRef.value) return
  try {
    await loadGsi()
  } catch (e) {
    return
  }
  window.google.accounts.id.initialize({
    client_id: clientId,
    callback: handleGoogleCredential
  })
  window.google.accounts.id.renderButton(googleBtnRef.value, {
    theme: 'outline', size: 'large', width: 280, text: 'signin_with', locale: 'ko'
  })
}

onMounted(initGoogleButton)
onBeforeUnmount(() => {
  window.google?.accounts?.id?.cancel?.()
})

function handleBtnClick (mode) {
  appStore.changeModalStatus({ mode, visible: true })
}

async function handleLogin () {
  const valid = await validateForm(formRef.value)
  if (!valid) return
  btnLoginLoading.value = true
  const formData = { ...formLogin.value }
  try {
    await api.login(formData)
    btnLoginLoading.value = false
    appStore.changeModalStatus({ visible: false })
    userStore.getProfile()
    ElMessage.success('OJ에 오신 것을 환영합니다')
  } catch (e) {
    btnLoginLoading.value = false
  }
}

function goResetPassword () {
  appStore.changeModalStatus({ visible: false })
  router.push({ name: 'apply-reset-password' })
}
</script>

<style scoped lang="less">
  .footer {
    overflow: auto;
    margin-top: 20px;
    margin-bottom: -15px;
    text-align: left;
    .btn {
      margin: 0 0 15px 0;
      width: 100%;
    }
    .divider {
    margin: 24px 0 16px;
    font-size: 13px;
    color: #909399;
  }

  .google-btn {
    display: flex;
    justify-content: center;
  }

  .notice {
    margin-bottom: 8px;
  }

  .forget-link {
      float: right;
    }
  }
</style>
