<template>
  <div class="view">
    <Panel title="SMTP 설정">
      <el-form label-position="left" label-width="70px" :model="smtp">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="서버" required><el-input v-model="smtp.server" placeholder="SMTP 서버 주소" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="포트" required><el-input type="number" v-model="smtp.port" placeholder="SMTP 서버 포트" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="이메일" required><el-input v-model="smtp.email" placeholder="발신 계정" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="비밀번호" label-width="90px" required>
              <el-input v-model="smtp.password" type="password" placeholder="SMTP 서버 비밀번호" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="TLS"><el-switch v-model="smtp.tls" /></el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <el-button type="primary" @click="saveSMTPConfig">저장</el-button>
      <el-button type="warning" @click="testSMTPConfig" v-if="saved" :loading="loadingBtnTest">테스트 메일 발송</el-button>
    </Panel>

    <Panel title="웹사이트 설정">
      <el-form label-position="left" label-width="100px" :model="websiteConfig">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="기본 URL" required><el-input v-model="websiteConfig.website_base_url" placeholder="사이트 기본 URL" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="이름" required><el-input v-model="websiteConfig.website_name" placeholder="사이트 이름" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="단축명" required><el-input v-model="websiteConfig.website_name_shortcut" placeholder="사이트 짧은 이름" /></el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="푸터" required>
              <el-input type="textarea" :autosize="{ minRows: 2, maxRows: 4 }" v-model="websiteConfig.website_footer" placeholder="사이트 푸터 HTML" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="회원가입 허용" label-width="200px">
              <el-switch v-model="websiteConfig.allow_register" active-color="#13ce66" inactive-color="#ff4949" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="모든 제출 내역 표시" label-width="200px">
              <el-switch v-model="websiteConfig.submission_list_show_all" active-color="#13ce66" inactive-color="#ff4949" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <save @click="saveWebsiteConfig" />
    </Panel>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessageBox, ElNotification } from 'element-plus'
import api from '../../api.js'

const isInit = ref(false)
const saved = ref(false)
const loadingBtnTest = ref(false)
const smtp = reactive({ server: 'smtp.example.com', port: 25, password: '', email: 'email@example.com', tls: true })
const websiteConfig = ref({})

onMounted(() => {
  api.getSMTPConfig().then(res => {
    if (res.data.data) {
      Object.assign(smtp, res.data.data)
    } else {
      isInit.value = true
      ElNotification.warning({ title: '경고', message: '먼저 SMTP 설정을 완료하세요' })
    }
  })
  api.getWebsiteConfig().then(res => {
    websiteConfig.value = res.data.data
  }).catch(() => {})
})

function saveSMTPConfig () {
  if (!isInit.value) {
    api.editSMTPConfig(smtp).then(() => { saved.value = true }, () => {})
  } else {
    api.createSMTPConfig(smtp).then(() => { saved.value = true }, () => {})
  }
}

function testSMTPConfig () {
  ElMessageBox.prompt('이메일을 입력하세요', '', {
    inputPattern: /[\w!#$%&'*+/=?^_`{|}~-]+(?:\.[\w!#$%&'*+/=?^_`{|}~-]+)*@(?:[\w](?:[\w-]*[\w])?\.)+[\w](?:[\w-]*[\w])?/,
    inputErrorMessage: 'Error email format'
  }).then(({ value }) => {
    loadingBtnTest.value = true
    api.testSMTPConfig(value).then(() => { loadingBtnTest.value = false }, () => { loadingBtnTest.value = false })
  }).catch(() => {})
}

function saveWebsiteConfig () {
  api.editWebsiteConfig(websiteConfig.value).then(() => {}).catch(() => {})
}
</script>
