<template>
  <div class="setting-main">
    <div class="section-title">{{ t('m.Avatar_Setting') }}</div>
    <el-upload
      class="mini-container"
      drag
      accept=".jpg,.jpeg,.png,.bmp,.gif"
      :show-file-list="false"
      :before-upload="handleSelectFile"
      :http-request="uploadAvatar"
      action=""
    >
      <el-icon :size="52" class="upload-icon"><UploadFilled /></el-icon>
      <div>Drop here, or click to select manually (max 2MB)</div>
    </el-upload>

    <div class="section-title">{{ t('m.Profile_Setting') }}</div>
    <el-form ref="formRef" :model="formProfile">
      <el-row type="flex" :gutter="30" justify="space-around">
        <el-col :span="11">
          <el-form-item label="Real Name">
            <el-input v-model="formProfile.real_name" />
          </el-form-item>
          <el-form-item label="School">
            <el-input v-model="formProfile.school" />
          </el-form-item>
          <el-form-item label="Major">
            <el-input v-model="formProfile.major" />
          </el-form-item>
          <el-form-item label="Language">
            <el-select v-model="formProfile.language">
              <el-option v-for="lang in languages" :key="lang.value" :value="lang.value" :label="lang.label" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="loadingSaveBtn" @click="updateProfile">Save All</el-button>
          </el-form-item>
        </el-col>

        <el-col :span="11">
          <el-form-item label="Mood">
            <el-input v-model="formProfile.mood" />
          </el-form-item>
          <el-form-item label="Blog">
            <el-input v-model="formProfile.blog" />
          </el-form-item>
          <el-form-item label="Github">
            <el-input v-model="formProfile.github" />
          </el-form-item>
        </el-col>
      </el-row>
    </el-form>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElNotification } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import api from '@oj/api'
import utils from '@/utils/utils'
import { languages } from '@/i18n'
import { useUserStore } from '@/store/user'

const { t } = useI18n()
const userStore = useUserStore()

const loadingSaveBtn = ref(false)
const formProfile = ref({
  real_name: '',
  mood: '',
  major: '',
  blog: '',
  school: '',
  github: '',
  language: ''
})

function checkFileType (file) {
  if (!/\.(gif|jpg|jpeg|png|bmp|GIF|JPG|PNG)$/.test(file.name)) {
    ElNotification.warning({ title: 'File type not support', message: `The format of ${file.name} is incorrect, please choose image only.` })
    return false
  }
  return true
}

function checkFileSize (file) {
  if (file.size > 2 * 1024 * 1024) {
    ElNotification.warning({ title: 'Exceed max size limit', message: `File ${file.name} is too big, you can upload a image up to 2MB in size` })
    return false
  }
  return true
}

function handleSelectFile (file) {
  return checkFileType(file) && checkFileSize(file)
}

function uploadAvatar ({ file }) {
  const form = new window.FormData()
  form.append('image', file)
  axios({
    method: 'post',
    url: 'upload_avatar',
    data: form,
    headers: { 'content-type': 'multipart/form-data' }
  }).then(() => {
    ElMessage.success('Successfully set new avatar')
    userStore.getProfile()
  }).catch(() => {})
}

function updateProfile () {
  loadingSaveBtn.value = true
  const updateData = utils.filterEmptyValue({ ...formProfile.value })
  api.updateProfile(updateData).then((res) => {
    ElMessage.success('Success')
    userStore.changeProfile(res.data.data)
    loadingSaveBtn.value = false
  }, () => {
    loadingSaveBtn.value = false
  })
}

onMounted(() => {
  const profile = userStore.profile
  Object.keys(formProfile.value).forEach((key) => {
    if (profile[key] !== undefined) {
      formProfile.value[key] = profile[key]
    }
  })
})
</script>

<style scoped>
.upload-icon {
  color: #3399ff;
}
</style>
