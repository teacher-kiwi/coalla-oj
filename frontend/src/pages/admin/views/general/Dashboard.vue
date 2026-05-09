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
          <p class="last-info-title">{{ t('m.Last_Login') }}</p>
          <el-form label-width="80px" class="last-info-body">
            <el-form-item label="Time:">
              <span>{{ localtime(session.last_activity) }}</span>
            </el-form-item>
            <el-form-item label="IP:">
              <span>{{ session.ip }}</span>
            </el-form-item>
            <el-form-item label="OS">
              <span>{{ os }}</span>
            </el-form-item>
            <el-form-item label="Browser:">
              <span>{{ browser }}</span>
            </el-form-item>
          </el-form>
        </div>
      </el-card>
      <Panel :title="t('m.System_Overview')" v-if="userStore.isSuperAdmin">
        <p>{{ t('m.DashBoardJudge_Server') }}: {{ infoData.judge_server_count }}</p>
        <p>{{ t('m.HTTPS_Status') }}:
          <el-tag :type="https ? 'success' : 'danger'" size="small">{{ https ? 'Enabled' : 'Disabled' }}</el-tag>
        </p>
        <p>{{ t('m.Force_HTTPS') }}:
          <el-tag :type="forceHttps ? 'success' : 'danger'" size="small">{{ forceHttps ? 'Enabled' : 'Disabled' }}</el-tag>
        </p>
        <p>{{ t('m.CDN_HOST') }}:
          <el-tag :type="cdn ? 'success' : 'warning'" size="small">{{ cdn ? cdn : 'Not Use' }}</el-tag>
        </p>
      </Panel>
    </el-col>

    <el-col :md="14" :lg="16" v-if="userStore.isSuperAdmin">
      <div class="info-container">
        <InfoCard color="#909399" icon="User" message="Total Users" iconSize="30px" class="info-item"
                  :value="infoData.user_count" />
        <InfoCard color="#67C23A" icon="List" message="Today Submissions" class="info-item"
                  :value="infoData.today_submission_count" />
        <InfoCard color="#409EFF" icon="Trophy" message="Recent Contests" class="info-item"
                  :value="infoData.recent_contest_count" />
      </div>
      <Panel class="release-panel">
        <template #title>
          <span v-loading="loadingReleases">Release Notes
            <el-popover placement="right" trigger="hover">
              <template #reference><el-icon class="help-icon"><QuestionFilled /></el-icon></template>
              <p>Please upgrade to the latest version to enjoy the new features.</p>
            </el-popover>
          </span>
        </template>
        <el-collapse v-model="activeNames">
          <el-collapse-item v-for="(release, index) in releases" :key="'release' + index" :name="index + 1">
            <template #title>
              <div v-if="release.new_version">{{ release.title }}
                <el-tag size="small" type="success">New Version</el-tag>
              </div>
              <span v-else>{{ release.title }}</span>
            </template>
            <p>Level: {{ release.level }}</p>
            <p>Details:</p>
            <div class="release-body">
              <ul v-for="detail in release.details" :key="detail">
                <li v-html="detail"></li>
              </ul>
            </div>
          </el-collapse-item>
        </el-collapse>
      </Panel>
    </el-col>
  </el-row>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { QuestionFilled } from '@element-plus/icons-vue'
import InfoCard from '@admin/components/infoCard.vue'
import api from '@admin/api'
import time from '@/utils/time'
import { useUserStore } from '@/store/user'

const { t } = useI18n()
const userStore = useUserStore()

const infoData = reactive({
  user_count: 0,
  recent_contest_count: 0,
  today_submission_count: 0,
  judge_server_count: 0,
  env: {}
})
const activeNames = ref([1])
const session = ref({})
const loadingReleases = ref(true)
const releases = ref([])

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
  api.getReleaseNotes().then(resp => {
    loadingReleases.value = false
    const data = resp.data.data
    if (!data) return
    const currentVersion = data.local_version
    data.update.forEach(release => {
      if (release.version > currentVersion) release.new_version = true
    })
    releases.value = data.update
  }, () => {
    loadingReleases.value = false
  })
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

  .release-panel {
    margin-top: 5px;
  }

  .help-icon {
    margin-left: 4px;
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
