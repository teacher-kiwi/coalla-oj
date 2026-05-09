<template>
  <div class="setting-main">
    <p class="section-title">{{ t('m.Sessions') }}</p>
    <div class="flex-container setting-content">
      <el-card v-for="session in sessions" :key="session.session_key" :body-style="{ padding: '20px' }" class="flex-child">
        <template #header>
          <div class="card-header">
            <span>{{ session.ip }}</span>
            <el-tag v-if="session.current_session" type="success">Current</el-tag>
            <el-button v-else type="warning" size="small" @click="deleteSession(session.session_key)">Revoke</el-button>
          </div>
        </template>
        <el-form label-width="120px">
          <el-form-item label="OS :" class="item">{{ getPlatform(session.user_agent) }}</el-form-item>
          <el-form-item label="Browser :" class="item">{{ getBrowser(session.user_agent) }}</el-form-item>
          <el-form-item label="Last Activity :" class="item">{{ localtime(session.last_activity) }}</el-form-item>
        </el-form>
      </el-card>
    </div>

    <p class="section-title">{{ t('m.Two_Factor_Authentication') }}</p>
    <div class="mini-container setting-content">
      <el-form>
        <el-alert v-if="TFAOpened" type="success" class="notice" show-icon :closable="false">
          You have enabled two-factor authentication.
        </el-alert>
        <el-form-item v-if="!TFAOpened">
          <div v-loading="loadingQRcode" class="oj-relative">
            <img :src="qrcodeSrc" id="qr-img" />
          </div>
        </el-form-item>
        <template v-if="!loadingQRcode">
          <el-form-item class="tfa-input">
            <el-input v-model="formTwoFactor.code" placeholder="Enter the code from your application" />
          </el-form-item>
          <el-button v-if="!TFAOpened" type="primary" :loading="loadingBtn" @click="updateTFA(false)">Open TFA</el-button>
          <el-button v-else type="danger" :loading="loadingBtn" @click="closeTFA">Close TFA</el-button>
        </template>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessageBox } from 'element-plus'
import api from '@oj/api'
import time from '@/utils/time'
import { useUserStore } from '@/store/user'

const { t } = useI18n()
const userStore = useUserStore()

const qrcodeSrc = ref('')
const loadingQRcode = ref(false)
const loadingBtn = ref(false)
const formTwoFactor = reactive({ code: '' })
const sessions = ref([])

const TFAOpened = computed(() => userStore.user && userStore.user.two_factor_auth)

function getBrowser (userAgent = '') {
  if (!userAgent) return 'Unknown'
  if (userAgent.includes('Chrome')) return 'Chrome'
  if (userAgent.includes('Firefox')) return 'Firefox'
  if (userAgent.includes('Safari')) return 'Safari'
  if (userAgent.includes('Edge')) return 'Edge'
  return 'Unknown'
}
function getPlatform (userAgent = '') {
  if (!userAgent) return 'Unknown'
  if (userAgent.includes('Windows')) return 'Windows'
  if (userAgent.includes('Mac OS')) return 'macOS'
  if (userAgent.includes('Linux')) return 'Linux'
  if (userAgent.includes('Android')) return 'Android'
  if (userAgent.includes('iPhone') || userAgent.includes('iPad')) return 'iOS'
  return 'Unknown'
}
function localtime (val) {
  return time.utcToLocal(val)
}

function getAuthImg () {
  loadingQRcode.value = true
  api.twoFactorAuth('get').then((res) => {
    loadingQRcode.value = false
    qrcodeSrc.value = res.data.data
  })
}

function getSessions () {
  api.getSessions().then((res) => {
    const data = res.data.data
    const sorted = data.filter((s) => s.current_session)
    data.forEach((s) => {
      if (!s.current_session) sorted.push(s)
    })
    sessions.value = sorted
  })
}

function deleteSession (sessionKey) {
  ElMessageBox.confirm('Are you sure to revoke the session?', 'Confirm').then(() => {
    api.deleteSession(sessionKey).then(getSessions)
  }).catch(() => {})
}

function closeTFA () {
  ElMessageBox.confirm('Two-factor Authentication is a powerful tool to protect your account, are you sure to close it?', 'Confirm').then(() => {
    updateTFA(true)
  }).catch(() => {})
}

function updateTFA (close) {
  const method = close === false ? 'post' : 'put'
  loadingBtn.value = true
  api.twoFactorAuth(method, { code: formTwoFactor.code }).then(() => {
    loadingBtn.value = false
    userStore.getProfile()
    if (close === true) getAuthImg()
    formTwoFactor.code = ''
  }, (err) => {
    formTwoFactor.code = ''
    loadingBtn.value = false
    if (err?.data?.data?.indexOf('session') > -1) {
      userStore.getProfile()
      getAuthImg()
    }
  })
}

onMounted(() => {
  getSessions()
  if (!TFAOpened.value) getAuthImg()
})
</script>

<style lang="less" scoped>
  .notice {
    font-size: 16px;
    margin-bottom: 20px;
    display: inline-block;
  }

  .oj-relative {
    width: 150px;
    #qr-img {
      width: 300px;
      margin: -10px 0 -30px -20px;
    }
  }

  .flex-container {
    display: flex;
    flex-flow: row wrap;
    justify-content: flex-start;
    .flex-child {
      flex: 1 0;
      max-width: 350px;
      margin-right: 30px;
      margin-bottom: 30px;
      .item {
        margin-bottom: 0;
      }
    }
  }

  .tfa-input {
    width: 250px;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
</style>
