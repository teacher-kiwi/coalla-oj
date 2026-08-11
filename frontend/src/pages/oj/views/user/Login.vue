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
  </div>
</template>

<script setup>
import { ref } from 'vue'
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
    .forget-link {
      float: right;
    }
  }
</style>
