<template>
  <div>
    <el-form ref="formRef" :model="formRegister" :rules="ruleRegister">
      <el-form-item prop="username">
        <el-input v-model="formRegister.username" :placeholder="t('m.RegisterUsername')" size="large" :prefix-icon="User" @keyup.enter="handleRegister" />
      </el-form-item>
      <el-form-item prop="email">
        <el-input v-model="formRegister.email" :placeholder="t('m.Email_Address')" size="large" :prefix-icon="Message" @keyup.enter="handleRegister" />
      </el-form-item>
      <el-form-item prop="password">
        <el-input type="password" v-model="formRegister.password" :placeholder="t('m.RegisterPassword')" size="large" :prefix-icon="Lock" @keyup.enter="handleRegister" />
      </el-form-item>
      <el-form-item prop="passwordAgain">
        <el-input type="password" v-model="formRegister.passwordAgain" :placeholder="t('m.Password_Again')" size="large" :prefix-icon="Lock" @keyup.enter="handleRegister" />
      </el-form-item>
      <el-form-item prop="captcha" class="captcha-item">
        <div class="oj-captcha">
          <div class="oj-captcha-code">
            <el-input v-model="formRegister.captcha" :placeholder="t('m.Captcha')" size="large" :prefix-icon="Key" @keyup.enter="handleRegister" />
          </div>
          <div class="oj-captcha-img">
            <el-tooltip content="Click to refresh" placement="top">
              <img :src="captchaSrc" @click="getCaptchaSrc" />
            </el-tooltip>
          </div>
        </div>
      </el-form-item>
    </el-form>
    <div class="footer">
      <div class="age-notice">
        만 14세 미만 아동은 직접 가입이 제한됩니다.<br />
        학교 수업용 계정이 필요한 경우 담당 선생님께 요청하세요.
      </div>
      <el-checkbox v-model="ageConfirmed" class="age-checkbox">
        <span class="required-tag">*</span> 본인은 만 14세 이상입니다.
      </el-checkbox>
      <el-button type="primary" class="btn" :loading="btnRegisterLoading" :disabled="!ageConfirmed" @click="handleRegister">
        {{ t('m.UserRegister') }}
      </el-button>
      <el-button class="btn" @click="switchMode('login')">
        {{ t('m.Already_Registed') }}
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { User, Lock, Message, Key } from '@element-plus/icons-vue'
import api from '@oj/api'
import { useForm } from '@oj/components/mixins'
import { useAppStore } from '@/store/app'

const { t } = useI18n()
const appStore = useAppStore()
const { captchaSrc, validateForm, getCaptchaSrc } = useForm()

const formRef = ref(null)
const btnRegisterLoading = ref(false)
const ageConfirmed = ref(false)
const formRegister = ref({
  username: '',
  password: '',
  passwordAgain: '',
  email: '',
  captcha: ''
})

const CheckUsernameNotExist = (rule, value, callback) => {
  api.checkUsernameOrEmail(value, undefined).then((res) => {
    if (res.data.data.username === true) callback(new Error(t('m.The_username_already_exists')))
    else callback()
  }, () => callback())
}
const CheckEmailNotExist = (rule, value, callback) => {
  api.checkUsernameOrEmail(undefined, value).then((res) => {
    if (res.data.data.email === true) callback(new Error(t('m.The_email_already_exists')))
    else callback()
  }, () => callback())
}
const CheckPassword = (rule, value, callback) => {
  if (formRegister.value.password !== '') {
    formRef.value?.validateField('passwordAgain')
  }
  callback()
}
const CheckAgainPassword = (rule, value, callback) => {
  if (value !== formRegister.value.password) callback(new Error(t('m.password_does_not_match')))
  else callback()
}

const ruleRegister = {
  username: [
    { required: true, trigger: 'blur' },
    { validator: CheckUsernameNotExist, trigger: 'blur' }
  ],
  email: [
    { required: true, type: 'email', trigger: 'blur' },
    { validator: CheckEmailNotExist, trigger: 'blur' }
  ],
  password: [
    { required: true, trigger: 'blur', min: 6, max: 20 },
    { validator: CheckPassword, trigger: 'blur' }
  ],
  passwordAgain: [
    { required: true, validator: CheckAgainPassword, trigger: 'change' }
  ],
  captcha: [{ required: true, trigger: 'blur', min: 1, max: 10 }]
}

function switchMode (mode) {
  appStore.changeModalStatus({ mode, visible: true })
}

async function handleRegister () {
  if (!ageConfirmed.value) {
    ElMessage.error('만 14세 이상 확인에 동의해주세요.')
    return
  }
  const valid = await validateForm(formRef.value)
  if (!valid) return
  const formData = { ...formRegister.value }
  delete formData.passwordAgain
  btnRegisterLoading.value = true
  try {
    await api.register(formData)
    ElMessage.success(t('m.Thanks_for_registering'))
    switchMode('login')
    btnRegisterLoading.value = false
  } catch (e) {
    getCaptchaSrc()
    formRegister.value.captcha = ''
    btnRegisterLoading.value = false
  }
}

onMounted(getCaptchaSrc)
</script>

<style scoped lang="less">
.captcha-item {
  margin-bottom: 10px;
}
.footer {
  overflow: auto;
  margin-top: 20px;
  margin-bottom: -15px;
  text-align: left;
  .btn {
    margin: 0 0 15px 0;
    width: 100%;
  }
}
.age-notice {
  font-size: 13px;
  color: #e6a23c;
  margin-bottom: 15px;
  line-height: 1.6;
}
.age-checkbox {
  display: block;
  margin-bottom: 15px;
  font-size: 13px;
}
.required-tag {
  color: #ed4014;
  font-weight: bold;
}
.oj-captcha {
  display: flex;
  .oj-captcha-code {
    flex: 1;
  }
  .oj-captcha-img {
    margin-left: 10px;
  }
}
</style>
