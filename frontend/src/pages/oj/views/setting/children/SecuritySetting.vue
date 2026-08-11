<template>
  <div class="setting-main">
    <p class="section-title">세션</p>
    <div class="flex-container setting-content">
      <el-card v-for="session in sessions" :key="session.session_key" :body-style="{ padding: '20px' }" class="flex-child">
        <template #header>
          <div class="card-header">
            <span>{{ session.ip }}</span>
            <el-tag v-if="session.current_session" type="success">현재 세션</el-tag>
            <el-button v-else type="warning" size="small" @click="deleteSession(session.session_key)">해제</el-button>
          </div>
        </template>
        <el-form label-width="120px">
          <el-form-item label="OS :" class="item">{{ getPlatform(session.user_agent) }}</el-form-item>
          <el-form-item label="브라우저 :" class="item">{{ getBrowser(session.user_agent) }}</el-form-item>
          <el-form-item label="마지막 활동 :" class="item">{{ localtime(session.last_activity) }}</el-form-item>
        </el-form>
      </el-card>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessageBox } from 'element-plus'
import api from '@oj/api'
import time from '@/utils/time'

const sessions = ref([])

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
  ElMessageBox.confirm('이 세션을 해제하시겠습니까?', '확인').then(() => {
    api.deleteSession(sessionKey).then(getSessions)
  }).catch(() => {})
}



onMounted(getSessions)
</script>

<style lang="less" scoped>
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

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
</style>
