<template>
  <div>
    <!-- 관리자는 /admin 에서 따로 로그인한다. 여기는 학생과 구글 계정(선생님·개인)만 둔다. -->
    <el-tabs v-model="tab" class="login-tabs">
      <el-tab-pane label="학생" name="student">
        <StudentLogin />
      </el-tab-pane>

      <el-tab-pane label="선생님·개인" name="google">
        <div v-if="appStore.website.google_client_id">
          <div v-if="needNickname">
            <p class="guide">처음 오셨네요. 사용하실 닉네임을 정해주세요.</p>
            <el-input v-model="nickname" placeholder="닉네임 (2~20자)" maxlength="20"
                      size="large" @keyup.enter="submitNickname" />
            <el-button type="primary" class="btn" :loading="btnLoginLoading"
                       @click="submitNickname">가입 완료</el-button>
          </div>
          <div v-show="!needNickname" ref="googleBtnRef" class="google-btn" />
        </div>
        <p v-else class="guide">
          구글 로그인이 아직 설정되지 않았습니다. 관리자에게 문의하세요.
        </p>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@oj/api'
import StudentLogin from '@oj/views/user/StudentLogin.vue'
import { renderGoogleButton } from '@/utils/google'
import { useAppStore } from '@/store/app'
import { useUserStore } from '@/store/user'

const appStore = useAppStore()
const userStore = useUserStore()

const tab = ref('student')
const googleBtnRef = ref(null)
const needNickname = ref(false)
const nickname = ref('')
let pendingCredential = null
const btnLoginLoading = ref(false)

async function googleLogin (credential, nick) {
  try {
    const res = await api.googleLogin(credential, nick)
    if (res.data.data?.status === 'nickname_required') {
      // 최초 가입이다. 닉네임을 받아 다시 보낸다.
      pendingCredential = credential
      needNickname.value = true
      return
    }
    appStore.changeModalStatus({ visible: false })
    needNickname.value = false
    userStore.getProfile()
    ElMessage.success('환영합니다')
  } catch (e) {
    // 에러 메시지는 api 인터셉터가 표시한다
  }
}

async function submitNickname () {
  if (!nickname.value.trim()) {
    ElMessage.error('닉네임을 입력해주세요')
    return
  }
  btnLoginLoading.value = true
  await googleLogin(pendingCredential, nickname.value.trim())
  btnLoginLoading.value = false
}

function initGoogleButton () {
  return renderGoogleButton(googleBtnRef.value, appStore.website.google_client_id, googleLogin)
}

// 숨겨진 탭에서 그리면 버튼 폭이 0 이 되므로, 탭이 열릴 때 그린다.
watch(tab, (value) => {
  if (value === 'google') nextTick(initGoogleButton)
})

onMounted(() => {
  if (tab.value === 'google') initGoogleButton()
})
onBeforeUnmount(() => {
  window.google?.accounts?.id?.cancel?.()
})
</script>

<style scoped lang="less">
.login-tabs {
  margin-top: -10px;
}

.btn {
  width: 100%;
  margin-top: 12px;
}

.google-btn {
  display: flex;
  justify-content: center;
  padding: 10px 0;
}

.guide {
  font-size: 13px;
  color: #606266;
  line-height: 1.7;
  margin-bottom: 10px;
}
</style>
