<template>
  <el-form :model="ruleForm" :rules="rules" ref="formRef" label-position="left" label-width="0px"
           class="demo-ruleForm login-container">
    <h3 class="title">{{ t('m.Welcome_to_Login') }}</h3>
    <el-form-item prop="account">
      <el-input v-model="ruleForm.account" :placeholder="t('m.username')" @keyup.enter="handleLogin" />
    </el-form-item>
    <el-form-item prop="password">
      <el-input type="password" v-model="ruleForm.password" :placeholder="t('m.password')" @keyup.enter="handleLogin" />
    </el-form-item>
    <el-form-item class="login-item">
      <el-button type="primary" class="login-btn" @click="handleLogin" :loading="logining">{{ t('m.GO') }}</el-button>
    </el-form-item>
  </el-form>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import api from '../../api'

const { t } = useI18n()
const router = useRouter()

const formRef = ref(null)
const logining = ref(false)
const ruleForm = reactive({ account: '', password: '' })
const rules = {
  account: [{ required: true, trigger: 'blur' }],
  password: [{ required: true, trigger: 'blur' }]
}

function handleLogin () {
  formRef.value.validate((valid) => {
    if (valid) {
      logining.value = true
      api.login(ruleForm.account, ruleForm.password).then(() => {
        logining.value = false
        router.push({ name: 'dashboard' })
      }, () => {
        logining.value = false
      })
    } else {
      ElMessage.error('Please check the error fields')
    }
  })
}
</script>

<style lang="less" scoped>
  .login-container {
    border-radius: 5px;
    margin: 180px auto;
    width: 350px;
    padding: 35px 35px 15px 35px;
    background: #fff;
    border: 1px solid #eaeaea;
    box-shadow: 0 0 25px #cac6c6;
    .title {
      margin: 0px auto 40px auto;
      text-align: center;
      color: #505458;
    }
    .login-item {
      width: 100%;
    }
    .login-btn {
      width: 100%;
    }
  }
</style>
