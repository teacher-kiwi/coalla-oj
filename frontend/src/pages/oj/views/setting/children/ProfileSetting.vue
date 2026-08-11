<template>
  <div class="setting-main">
    <div class="section-title">아바타 설정</div>
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

    <div class="section-title">프로필 설정</div>
    <el-form ref="formRef" :model="formProfile">
      <el-row type="flex" :gutter="30" justify="space-around">
        <el-col :span="11">
          <el-form-item label="실명">
            <el-input v-model="formProfile.real_name" />
          </el-form-item>
          <el-form-item label="학교">
            <el-input v-model="formProfile.school" />
          </el-form-item>
          <el-form-item label="전공">
            <el-input v-model="formProfile.major" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="loadingSaveBtn" @click="updateProfile">모두 저장</el-button>
          </el-form-item>
        </el-col>

        <el-col :span="11">
          <el-form-item label="기분">
            <el-input v-model="formProfile.mood" />
          </el-form-item>
          <el-form-item label="블로그">
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
import { ElMessage, ElNotification } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import api from '@oj/api'
import utils from '@/utils/utils'
import { useUserStore } from '@/store/user'
const userStore = useUserStore()

const loadingSaveBtn = ref(false)
const formProfile = ref({
  real_name: '',
  mood: '',
  major: '',
  blog: '',
  school: '',
  github: ''
})

function checkFileType (file) {
  if (!/\.(gif|jpg|jpeg|png|bmp|GIF|JPG|PNG)$/.test(file.name)) {
    ElNotification.warning({ title: '지원하지 않는 파일 형식입니다', message: `The format of ${file.name} is incorrect, please choose image only.` })
    return false
  }
  return true
}

function checkFileSize (file) {
  if (file.size > 2 * 1024 * 1024) {
    ElNotification.warning({ title: '파일 크기가 너무 큽니다', message: `File ${file.name} is too big, you can upload a image up to 2MB in size` })
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
    ElMessage.success('프로필 사진을 변경했습니다')
    userStore.getProfile()
  }).catch(() => {})
}

function updateProfile () {
  loadingSaveBtn.value = true
  const updateData = utils.filterEmptyValue({ ...formProfile.value })
  api.updateProfile(updateData).then((res) => {
    ElMessage.success('성공')
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
