<template>
  <el-row :gutter="20">
    <el-col :md="10" :lg="8">
      <el-card class="admin-info">
        <el-row :gutter="20">
          <el-col :span="10">
            <img class="avatar" :src="userStore.profile.avatar" />
          </el-col>
          <el-col :span="14">
            <p class="admin-info-name">{{ user.username }}</p>
            <p>{{ user.admin_type }}</p>
          </el-col>
        </el-row>
        <hr />
        <div class="last-info">
          <p class="last-info-title">마지막 로그인</p>
          <el-form label-width="80px" class="last-info-body">
            <el-form-item label="시간:">
              <span>{{ localtime(session.last_activity) }}</span>
            </el-form-item>
            <el-form-item label="IP:">
              <span>{{ session.ip }}</span>
            </el-form-item>
            <el-form-item label="OS">
              <span>{{ os }}</span>
            </el-form-item>
            <el-form-item label="브라우저:">
              <span>{{ browser }}</span>
            </el-form-item>
          </el-form>
        </div>
      </el-card>
      <Panel title="시스템 개요" v-if="userStore.isSuperAdmin">
        <p>채점 서버: {{ infoData.judge_server_count }}</p>
        <p>HTTPS 상태:
          <el-tag :type="https ? 'success' : 'danger'" size="small">{{ https ? 'Enabled' : 'Disabled' }}</el-tag>
        </p>
        <p>HTTPS 강제:
          <el-tag :type="forceHttps ? 'success' : 'danger'" size="small">{{ forceHttps ? 'Enabled' : 'Disabled' }}</el-tag>
        </p>
        <p>CDN 호스트:
          <el-tag :type="cdn ? 'success' : 'warning'" size="small">{{ cdn ? cdn : 'Not Use' }}</el-tag>
        </p>
      </Panel>
    </el-col>

    <el-col :md="14" :lg="16" v-if="userStore.isSuperAdmin">
      <div class="info-container">
        <InfoCard color="#909399" icon="User" message="전체 사용자" iconSize="30px" class="info-item"
                  :value="infoData.user_count" />
        <InfoCard color="#67C23A" icon="List" message="오늘 제출" class="info-item"
                  :value="infoData.today_submission_count" />
        <InfoCard color="#409EFF" icon="Trophy" message="최근 대회" class="info-item"
                  :value="infoData.recent_contest_count" />
      </div>
    </el-col>
  </el-row>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import InfoCard from '@admin/components/infoCard.vue'
import api from '@admin/api'
import time from '@/utils/time'
import { useUserStore } from '@/store/user'
const userStore = useUserStore()

const infoData = reactive({
  user_count: 0,
  recent_contest_count: 0,
  today_submission_count: 0,
  judge_server_count: 0,
  env: {}
})
const session = ref({})

const user = computed(() => userStore.user)
const cdn = computed(() => infoData.env.STATIC_CDN_HOST)
const https = computed(() => document.URL.slice(0, 5) === 'https')
const forceHttps = computed(() => infoData.env.FORCE_HTTPS)

const browser = computed(() => {
  const ua = session.value.user_agent || ''
  if (!ua) return 'Unknown'
  if (ua.includes('Chrome')) return 'Chrome'
  if (ua.includes('Firefox')) return 'Firefox'
  if (ua.includes('Safari')) return 'Safari'
  if (ua.includes('Edge')) return 'Edge'
  return 'Unknown'
})

const os = computed(() => {
  const ua = session.value.user_agent || ''
  if (!ua) return 'Unknown'
  if (ua.includes('Windows')) return 'Windows'
  if (ua.includes('Mac OS')) return 'macOS'
  if (ua.includes('Linux')) return 'Linux'
  if (ua.includes('Android')) return 'Android'
  if (ua.includes('iPhone') || ua.includes('iPad')) return 'iOS'
  return 'Unknown'
})

function localtime (val) {
  return time.utcToLocal(val)
}

onMounted(() => {
  api.getDashboardInfo().then(resp => {
    Object.assign(infoData, resp.data.data)
  }, () => {})
  api.getSessions().then(resp => {
    const sessions = resp.data.data
    let s = sessions[0]
    if (sessions.length > 1) {
      s = sessions.filter(x => !x.current_session).sort((a, b) => {
        return a.last_activity < b.last_activity ? 1 : -1
      })[0] || s
    }
    session.value = s
  }, () => {})
})
</script>

<style lang="less">
  .admin-info {
    margin-bottom: 20px;
    &-name {
      font-size: 24px;
      font-weight: 700;
      margin-bottom: 10px;
      color: #409EFF;
    }
    .avatar {
      max-width: 100%;
    }
    .last-info {
      &-title {
        font-size: 16px;
      }
      &-body {
        .el-form-item {
          margin-bottom: 5px;
        }
      }
    }
  }

  .info-container {
    display: flex;
    justify-content: flex-start;
    flex-wrap: wrap;
    .info-item {
      flex: 1 0 auto;
      min-width: 200px;
      margin-bottom: 10px;
    }
  }
</style>
