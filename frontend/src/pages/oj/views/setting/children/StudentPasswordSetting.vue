<template>
  <div class="setting-main">
    <p class="section-title">비밀번호 변경</p>
    <div class="mini-container setting-content">
      <p class="guide">
        숫자 4자리로 정해주세요. 잊어버리면 선생님께 말씀드리면 새로 만들어 주십니다.
      </p>
      <el-form label-width="140px">
        <el-form-item label="지금 비밀번호">
          <el-input v-model="form.old_password" type="password" inputmode="numeric"
                    maxlength="4" placeholder="숫자 4자리" class="pin-input" />
        </el-form-item>
        <el-form-item label="새 비밀번호">
          <el-input v-model="form.new_password" type="password" inputmode="numeric"
                    maxlength="4" placeholder="숫자 4자리" class="pin-input" />
        </el-form-item>
        <el-form-item label="새 비밀번호 확인">
          <el-input v-model="form.again" type="password" inputmode="numeric"
                    maxlength="4" placeholder="숫자 4자리" class="pin-input"
                    @keyup.enter="submit" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="submit">바꾸기</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@oj/api'
import { useAppStore } from '@/store/app'
import { useUserStore } from '@/store/user'

const router = useRouter()
const appStore = useAppStore()
const userStore = useUserStore()
const loading = ref(false)
const form = reactive({ old_password: '', new_password: '', again: '' })

function submit () {
  if (!/^\d{4}$/.test(form.new_password)) {
    ElMessage.error('새 비밀번호는 숫자 4자리입니다')
    return
  }
  if (form.new_password !== form.again) {
    ElMessage.error('새 비밀번호가 서로 다릅니다')
    return
  }
  loading.value = true
  api.studentChangePassword({
    old_password: form.old_password,
    new_password: form.new_password
  }).then(() => {
    loading.value = false
    form.old_password = form.new_password = form.again = ''
    // 비밀번호를 바꾸면 서버 세션이 끊긴다. 그대로 두면 다른 화면으로 옮길 때
    // 갑자기 로그인이 풀린 것처럼 보이므로, 바로 안내하고 로그인 화면으로 보낸다.
    userStore.clearProfile()
    ElMessageBox.alert('새로 정한 비밀번호로 다시 로그인해주세요.', '비밀번호를 바꿨습니다', {
      confirmButtonText: '로그인하러 가기'
    }).then(goLogin).catch(goLogin)
  }, () => {
    loading.value = false
  })
}

function goLogin () {
  router.push({ name: 'home' })
  appStore.changeModalStatus({ visible: true })
}
</script>

<style scoped>
.guide {
  font-size: 14px;
  color: #606266;
  line-height: 1.7;
  margin-bottom: 16px;
}

.pin-input {
  width: 160px;
}
</style>
