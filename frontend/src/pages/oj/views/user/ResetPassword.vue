<template>
  <Panel :padding="30" class="container">
    <template #title>
      <div class="center">{{ t('m.Reset_Password') }}</div>
    </template>
    <template v-if="!resetSuccess">
      <el-form ref="formRef" :model="formResetPassword" :rules="ruleResetPassword">
        <el-form-item prop="password">
          <el-input type="password" v-model="formResetPassword.password" :placeholder="t('m.RPassword')" size="large" :prefix-icon="Lock" />
        </el-form-item>
        <el-form-item prop="passwordAgain">
          <el-input type="password" v-model="formResetPassword.passwordAgain" :placeholder="t('m.RPassword_Again')" size="large" :prefix-icon="Lock" />
        </el-form-item>
        <el-form-item prop="captcha" class="captcha-item">
          <div id="captcha">
            <div id="captchaCode">
              <el-input v-model="formResetPassword.captcha" :placeholder="t('m.RCaptcha')" size="large" :prefix-icon="Key" />
            </div>
            <div id="captchaImg">
              <el-tooltip content="Click to refresh" placement="top">
                <img :src="captchaSrc" @click="getCaptchaSrc" />
              </el-tooltip>
            </div>
          </div>
        </el-form-item>
      </el-form>
      <el-button type="primary" class="btn" :loading="btnLoading" @click="resetPassword">
        {{ t('m.Reset_Password') }}
      </el-button>
    </template>
    <template v-else>
      <el-alert type="success" :closable="false">{{ t('m.Your_password_has_been_reset') }}</el-alert>
    </template>
  </Panel>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Lock, Key } from '@element-plus/icons-vue'
import api from '@oj/api'
import { useForm } from '@oj/components/mixins'

const { t } = useI18n()
const route = useRoute()
const { captchaSrc, validateForm, getCaptchaSrc } = useForm()

const formRef = ref(null)
const btnLoading = ref(false)
const resetSuccess = ref(false)
const formResetPassword = ref({ captcha: '', password: '', passwordAgain: '', token: '' })

const CheckPassword = (rule, value, callback) => {
  if (formResetPassword.value.passwordAgain !== '') {
    formRef.value?.validateField('passwordAgain')
  }
  callback()
}
const CheckAgainPassword = (rule, value, callback) => {
  if (value !== formResetPassword.value.password) callback(new Error(t('m.password_does_not_match')))
  else callback()
}

const ruleResetPassword = {
  password: [
    { required: true, trigger: 'blur', min: 6, max: 20 },
    { validator: CheckPassword, trigger: 'blur' }
  ],
  passwordAgain: [
    { required: true, validator: CheckAgainPassword, trigger: 'change' }
  ],
  captcha: [
    { required: true, trigger: 'blur', min: 1, max: 10 }
  ]
}

async function resetPassword () {
  const valid = await validateForm(formRef.value)
  if (!valid) return
  btnLoading.value = true
  const data = { ...formResetPassword.value }
  delete data.passwordAgain
  try {
    await api.resetPassword(data)
    btnLoading.value = false
    resetSuccess.value = true
  } catch (e) {
    btnLoading.value = false
    formResetPassword.value.captcha = ''
    getCaptchaSrc()
  }
}

onMounted(() => {
  formResetPassword.value.token = route.params.token
  getCaptchaSrc()
})
</script>

<style lang="less" scoped>
  .container {
    width: 450px;
    margin: auto;
    .center {
      text-align: center;
    }
    #captcha {
      display: flex;
      flex-wrap: nowrap;
      justify-content: space-between;
      width: 100%;
      height: 36px;
      #captchaCode {
        flex: auto;
      }
      #captchaImg {
        margin-left: 10px;
        padding: 3px;
        flex: initial;
      }
    }
    .captcha-item {
      margin-bottom: 10px;
    }
    .btn {
      margin-top: 18px;
      text-align: center;
      width: 100%;
    }
  }
</style>
