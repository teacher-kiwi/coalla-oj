<template>
  <div class="setting-main">
    <div class="flex-container">
      <div class="left">
        <p class="section-title">{{ t('m.ChangePassword') }}</p>
        <el-form class="setting-content" ref="formPasswordRef" :model="formPassword" :rules="rulePassword" label-width="160px">
          <el-form-item label="Old Password" prop="old_password">
            <el-input v-model="formPassword.old_password" type="password" />
          </el-form-item>
          <el-form-item label="New Password" prop="new_password">
            <el-input v-model="formPassword.new_password" type="password" />
          </el-form-item>
          <el-form-item label="Confirm New Password" prop="again_password">
            <el-input v-model="formPassword.again_password" type="password" />
          </el-form-item>
          <el-form-item v-if="visible.tfaRequired" label="Two Factor Auth" prop="tfa_code">
            <el-input v-model="formPassword.tfa_code" />
          </el-form-item>
          <el-form-item v-if="visible.passwordAlert">
            <el-alert type="success" :closable="false">You will need to login again after 5 seconds..</el-alert>
          </el-form-item>
          <el-button type="primary" :loading="loading.btnPassword" @click="changePassword">{{ t('m.Update_Password') }}</el-button>
        </el-form>
      </div>

      <div class="middle separator" />

      <div class="right">
        <p class="section-title">{{ t('m.ChangeEmail') }}</p>
        <el-form class="setting-content" ref="formEmailRef" :model="formEmail" :rules="ruleEmail" label-width="160px">
          <el-form-item label="Current Password" prop="password">
            <el-input v-model="formEmail.password" type="password" />
          </el-form-item>
          <el-form-item label="Old Email">
            <el-input v-model="formEmail.old_email" disabled />
          </el-form-item>
          <el-form-item label="New Email" prop="new_email">
            <el-input v-model="formEmail.new_email" />
          </el-form-item>
          <el-form-item v-if="visible.tfaRequired" label="Two Factor Auth" prop="tfa_code">
            <el-input v-model="formEmail.tfa_code" />
          </el-form-item>
          <el-button type="primary" :loading="loading.btnEmail" @click="changeEmail">{{ t('m.ChangeEmail') }}</el-button>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import api from '@oj/api'
import { useForm } from '@oj/components/mixins'
import { useUserStore } from '@/store/user'

const { t } = useI18n()
const router = useRouter()
const userStore = useUserStore()
const { validateForm } = useForm()

const formPasswordRef = ref(null)
const formEmailRef = ref(null)

const loading = reactive({ btnPassword: false, btnEmail: false })
const visible = reactive({ passwordAlert: false, emailAlert: false, tfaRequired: false })

const formPassword = ref({ tfa_code: '', old_password: '', new_password: '', again_password: '' })
const formEmail = ref({ tfa_code: '', password: '', old_email: '', new_email: '' })

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
const tfaCheck = [{ required: true, trigger: 'change' }]

const rulePassword = {
  old_password: oldPasswordCheck,
  new_password: [
    { required: true, trigger: 'blur', min: 6, max: 20 },
    { validator: CheckNewPassword, trigger: 'blur' }
  ],
  again_password: [
    { required: true, validator: CheckAgainPassword, trigger: 'change' }
  ],
  tfa_code: tfaCheck
}

const ruleEmail = {
  password: oldPasswordCheck,
  new_email: [{ required: true, type: 'email', trigger: 'change' }],
  tfa_code: tfaCheck
}

async function changePassword () {
  const valid = await validateForm(formPasswordRef.value)
  if (!valid) return
  loading.btnPassword = true
  const data = { ...formPassword.value }
  delete data.again_password
  if (!visible.tfaRequired) delete data.tfa_code
  try {
    await api.changePassword(data)
    loading.btnPassword = false
    visible.passwordAlert = true
    ElMessage.success('Update password successfully')
    setTimeout(() => {
      visible.passwordAlert = false
      router.push({ name: 'logout' })
    }, 5000)
  } catch (res) {
    if (res?.data?.data === 'tfa_required') visible.tfaRequired = true
    loading.btnPassword = false
  }
}

async function changeEmail () {
  const valid = await validateForm(formEmailRef.value)
  if (!valid) return
  loading.btnEmail = true
  const data = { ...formEmail.value }
  if (!visible.tfaRequired) delete data.tfa_code
  try {
    await api.changeEmail(data)
    loading.btnEmail = false
    visible.emailAlert = true
    ElMessage.success('Change email successfully')
    formEmailRef.value?.resetFields()
  } catch (res) {
    if (res?.data?.data === 'tfa_required') visible.tfaRequired = true
    loading.btnEmail = false
  }
}

onMounted(() => {
  formEmail.value.old_email = userStore.user.email || ''
})
</script>

<style lang="less" scoped>
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
