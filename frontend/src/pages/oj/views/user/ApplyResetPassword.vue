<template>
  <Panel :padding="30" class="container">
    <template #title>
      <div class="center">비밀번호 찾기</div>
    </template>
    <template v-if="!successApply">
      <el-form ref="formRef" :rules="ruleResetPassword" :model="formResetPassword">
        <el-form-item prop="email">
          <el-input v-model="formResetPassword.email" placeholder="이메일 주소" size="large" :prefix-icon="Message" />
        </el-form-item>
        <el-form-item prop="captcha" class="captcha-item">
          <div class="oj-captcha">
            <div class="oj-captcha-code">
              <el-input v-model="formResetPassword.captcha" placeholder="보안 문자" size="large" :prefix-icon="Key" />
            </div>
            <div class="oj-captcha-img">
              <el-tooltip content="클릭하면 새로고침" placement="top">
                <img :src="captchaSrc" @click="getCaptchaSrc" />
              </el-tooltip>
            </div>
          </div>
        </el-form-item>
      </el-form>
      <el-button type="primary" class="btn" :loading="btnLoading" @click="sendEmail">
        비밀번호 재설정 이메일 보내기
      </el-button>
    </template>
    <template v-else>
      <el-alert type="success" show-icon :closable="false">
        <template #title>성공</template>
        비밀번호 재설정 메일이 전송되었습니다
      </el-alert>
    </template>
  </Panel>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Message, Key } from '@element-plus/icons-vue'
import api from '@oj/api'
import { useForm } from '@oj/components/mixins'

const { captchaSrc, validateForm, getCaptchaSrc } = useForm()

const formRef = ref(null)
const successApply = ref(false)
const btnLoading = ref(false)
const formResetPassword = ref({ email: '', captcha: '' })

const CheckEmailExist = (rule, value, callback) => {
  if (value !== '') {
    api.checkUsernameOrEmail(undefined, value).then((res) => {
      if (res.data.data.email === false) callback(new Error('이메일이 존재하지 않습니다'))
      else callback()
    }, () => callback())
  } else {
    callback()
  }
}

const ruleResetPassword = {
  email: [
    { required: true, type: 'email', trigger: 'blur' },
    { validator: CheckEmailExist, trigger: 'blur' }
  ],
  captcha: [
    { required: true, trigger: 'blur', min: 1, max: 10 }
  ]
}

async function sendEmail () {
  const valid = await validateForm(formRef.value)
  if (!valid) return
  btnLoading.value = true
  try {
    await api.applyResetPassword(formResetPassword.value)
    setTimeout(() => {
      btnLoading.value = false
      successApply.value = true
    }, 2000)
  } catch (e) {
    btnLoading.value = false
    formResetPassword.value.captcha = ''
    getCaptchaSrc()
  }
}

onMounted(getCaptchaSrc)
</script>

<style scoped lang="less">
  .container {
    width: 450px;
    margin: auto;
    .center {
      text-align: center;
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
