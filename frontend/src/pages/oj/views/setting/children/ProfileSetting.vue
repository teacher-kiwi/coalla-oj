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
      <div>이미지를 끌어다 놓거나 클릭해서 선택하세요 (최대 2MB)</div>
    </el-upload>
  </div>
</template>

<script setup>
import axios from 'axios'
import { ElMessage, ElNotification } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { useUserStore } from '@/store/user'
const userStore = useUserStore()

// 남은 프로필 항목은 사진뿐이다. 학교·전공·블로그·GitHub·기분은 6단계에서,
// 실명은 학급 닉네임(ClassMembership.nickname)으로 옮기면서 없앴다.

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
</script>

<style scoped>
.upload-icon {
  color: #3399ff;
}
</style>
