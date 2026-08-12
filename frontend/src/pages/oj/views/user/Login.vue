<template>
  <div>
    <el-tabs v-model="tab" class="login-tabs">
      <el-tab-pane label="학생" name="student">
        <StudentLogin />
      </el-tab-pane>

      <el-tab-pane label="선생님·개인" name="google">
        <div v-if="appStore.website.google_client_id">
          <div v-if="needNickname">
            <p class="guide">처음 오셨네요. 사용하실 닉네임을 정해주세요.</p>
            <el-input v-model="nickname" placeholder="닉네임 (2~20자)" maxlength="20"
                      size="large" @keyup.enter="submitNickname" />
            <el-button type="primary" class="btn" :loading="btnLoginLoading"
                       @click="submitNickname">가입 완료</el-button>
          </div>
          <div v-show="!needNickname" ref="googleBtnRef" class="google-btn" />
        </div>
        <p v-else class="guide">
          구글 로그인이 아직 설정되지 않았습니다. 관리자에게 문의하세요.
        </p>
      </el-tab-pane>

      <el-tab-pane label="관리자" name="admin">
        <el-form ref="formRef" :model="formLogin" :rules="ruleLogin">
          <el-form-item prop="username">
            <el-input v-model="formLogin.username" placeholder="사용자명" size="large"
                      :prefix-icon="User" @keyup.enter="handleLogin" />
          </el-form-item>
          <el-form-item prop="password">
            <el-input type="password" v-model="formLogin.password" placeholder="비밀번호"
                      size="large" :prefix-icon="Lock" @keyup.enter="handleLogin" />
          </el-form-item>
        </el-form>
        <el-button type="primary" class="btn" :loading="btnLoginLoading" @click="handleLogin">
          로그인
        </el-button>
        <div class="footer">
          <a @click.stop="goResetPassword" class="forget-link">비밀번호 찾기</a>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import api from '@oj/api'
import StudentLogin from '@oj/views/user/StudentLogin.vue'
import { useForm } from '@oj/components/mixins'
import { useAppStore } from '@/store/app'
import { useUserStore } from '@/store/user'

const router = useRouter()
const appStore = useAppStore()
const userStore = useUserStore()
const { validateForm } = useForm()

const tab = ref('student')
const googleBtnRef = ref(null)
const needNickname = ref(false)
const nickname = ref('')
let pendingCredential = null
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

async function googleLogin (credential, nick) {
  try {
    const res = await api.googleLogin(credential, nick)
    if (res.data.data?.status === 'nickname_required') {
      // 최초 가입이다. 닉네임을 받아 다시 보낸다.
      pendingCredential = credential
      needNickname.value = true
      return
    }
    appStore.changeModalStatus({ visible: false })
    needNickname.value = false
    userStore.getProfile()
    ElMessage.success('환영합니다')
  } catch (e) {
    // 에러 메시지는 api 인터셉터가 표시한다
  }
}

function handleGoogleCredential (response) {
  googleLogin(response.credential)
}

async function submitNickname () {
  if (!nickname.value.trim()) {
    ElMessage.error('닉네임을 입력해주세요')
    return
  }
  btnLoginLoading.value = true
  await googleLogin(pendingCredential, nickname.value.trim())
  btnLoginLoading.value = false
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

// 숨겨진 탭에서 그리면 버튼 폭이 0 이 되므로, 탭이 열릴 때 그린다.
watch(tab, (value) => {
  if (value === 'google') nextTick(initGoogleButton)
})

onMounted(() => {
  if (tab.value === 'google') initGoogleButton()
})
onBeforeUnmount(() => {
  window.google?.accounts?.id?.cancel?.()
})

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
    ElMessage.success('환영합니다')
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
.login-tabs {
  margin-top: -10px;
}

.btn {
  width: 100%;
  margin-top: 12px;
}

.footer {
  overflow: auto;
  margin-top: 16px;
  text-align: left;

  a {
    display: block;
    font-size: 13px;
    margin-top: 6px;
  }
}

.google-btn {
  display: flex;
  justify-content: center;
  padding: 10px 0;
}

.guide {
  font-size: 13px;
  color: #606266;
  line-height: 1.7;
  margin-bottom: 10px;
}
</style>
