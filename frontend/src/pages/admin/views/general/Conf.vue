<template>
  <div class="view">
    <Panel :title="t('m.SMTP_Config')">
      <el-form label-position="left" label-width="70px" :model="smtp">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item :label="t('m.Server')" required><el-input v-model="smtp.server" placeholder="SMTP Server Address" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="t('m.Port')" required><el-input type="number" v-model="smtp.port" placeholder="SMTP Server Port" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="t('m.Email')" required><el-input v-model="smtp.email" placeholder="Account Used To Send Email" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="t('m.Password')" label-width="90px" required>
              <el-input v-model="smtp.password" type="password" placeholder="SMTP Server Password" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="TLS"><el-switch v-model="smtp.tls" /></el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <el-button type="primary" @click="saveSMTPConfig">Save</el-button>
      <el-button type="warning" @click="testSMTPConfig" v-if="saved" :loading="loadingBtnTest">Send Test Email</el-button>
    </Panel>

    <Panel :title="t('m.Website_Config')">
      <el-form label-position="left" label-width="100px" :model="websiteConfig">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item :label="t('m.Base_Url')" required><el-input v-model="websiteConfig.website_base_url" placeholder="Website Base Url" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="t('m.Name')" required><el-input v-model="websiteConfig.website_name" placeholder="Website Name" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="t('m.Shortcut')" required><el-input v-model="websiteConfig.website_name_shortcut" placeholder="Website Name Shortcut" /></el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item :label="t('m.Footer')" required>
              <el-input type="textarea" :autosize="{ minRows: 2, maxRows: 4 }" v-model="websiteConfig.website_footer" placeholder="Website Footer HTML" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="t('m.Allow_Register')" label-width="200px">
              <el-switch v-model="websiteConfig.allow_register" active-color="#13ce66" inactive-color="#ff4949" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="t('m.Submission_List_Show_All')" label-width="200px">
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
import { useI18n } from 'vue-i18n'
import { ElMessageBox, ElNotification } from 'element-plus'
import api from '../../api.js'

const { t } = useI18n()

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
      ElNotification.warning({ title: 'Warning', message: 'Please setup SMTP config at first' })
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
  ElMessageBox.prompt('Please input your email', '', {
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
