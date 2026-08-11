<template>
  <Panel :padding="30" class="container">
    <template #title>
      <div class="center">비밀번호 찾기</div>
    </template>
    <template v-if="!resetSuccess">
      <el-form ref="formRef" :model="formResetPassword" :rules="ruleResetPassword">
        <el-form-item prop="password">
          <el-input type="password" v-model="formResetPassword.password" placeholder="비밀번호" size="large" :prefix-icon="Lock" />
        </el-form-item>
        <el-form-item prop="passwordAgain">
          <el-input type="password" v-model="formResetPassword.passwordAgain" placeholder="비밀번호 확인" size="large" :prefix-icon="Lock" />
        </el-form-item>
        <el-form-item prop="captcha" class="captcha-item">
          <div id="captcha">
            <div id="captchaCode">
              <el-input v-model="formResetPassword.captcha" placeholder="보안 문자" size="large" :prefix-icon="Key" />
            </div>
            <div id="captchaImg">
              <el-tooltip content="클릭하면 새로고침" placement="top">
                <img :src="captchaSrc" @click="getCaptchaSrc" />
              </el-tooltip>
            </div>
          </div>
        </el-form-item>
      </el-form>
      <el-button type="primary" class="btn" :loading="btnLoading" @click="resetPassword">
        비밀번호 찾기
      </el-button>
    </template>
    <template v-else>
      <el-alert type="success" :closable="false">비밀번호가 재설정되었습니다.</el-alert>
    </template>
  </Panel>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { Lock, Key } from '@element-plus/icons-vue'
import api from '@oj/api'
import { useForm } from '@oj/components/mixins'
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
  if (value !== formResetPassword.value.password) callback(new Error('비밀번호가 일치하지 않습니다'))
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
