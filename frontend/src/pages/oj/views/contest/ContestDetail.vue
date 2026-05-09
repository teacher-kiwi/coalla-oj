<template>
  <div class="flex-container">
    <div id="contest-main">
      <!--children-->
      <router-view v-slot="{ Component }">
        <transition name="fadeInUp">
          <component :is="Component" />
        </transition>
      </router-view>
      <!--children end-->
      <div class="flex-container" v-if="route_name === 'contest-details'">
        <div id="contest-desc">
          <Panel :padding="20" shadow>
            <template #title>{{ contest.title }}</template>
            <template #extra>
              <el-tag :type="countdownType">
                <span id="countdown">{{ countdown }}</span>
              </el-tag>
            </template>
            <div v-html="contest.description" class="markdown-body"></div>
            <div v-if="passwordFormVisible" class="contest-password">
              <el-input v-model="contestPassword" type="password"
                        placeholder="contest password" class="contest-password-input"
                        @keyup.enter="checkPassword" />
              <el-button type="primary" @click="checkPassword">Enter</el-button>
            </div>
          </Panel>
          <el-table :data="contestTable" class="contest-info-table">
            <el-table-column :label="t('m.StartAt')">
              <template #default="{ row }">{{ localtime(row.start_time) }}</template>
            </el-table-column>
            <el-table-column :label="t('m.EndAt')">
              <template #default="{ row }">{{ localtime(row.end_time) }}</template>
            </el-table-column>
            <el-table-column :label="t('m.ContestType')">
              <template #default="{ row }">{{ row.contest_type ? t('m.' + row.contest_type.replace(' ', '_')) : '' }}</template>
            </el-table-column>
            <el-table-column :label="t('m.Rule')">
              <template #default="{ row }">{{ row.rule_type ? t('m.' + row.rule_type) : '' }}</template>
            </el-table-column>
            <el-table-column :label="t('m.Creator')">
              <template #default="{ row }">{{ row.created_by.username }}</template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </div>

    <div v-show="showMenu" id="contest-menu">
      <VerticalMenu @on-click="handleRoute">
        <VerticalMenuItem :route="{ name: 'contest-details', params: { contestID } }">
          <el-icon><House /></el-icon>
          {{ t('m.Overview') }}
        </VerticalMenuItem>
        <VerticalMenuItem :disabled="contestMenuDisabled"
                          :route="{ name: 'contest-announcement-list', params: { contestID } }">
          <el-icon><ChatDotRound /></el-icon>
          {{ t('m.Announcements') }}
        </VerticalMenuItem>
        <VerticalMenuItem :disabled="contestMenuDisabled"
                          :route="{ name: 'contest-problem-list', params: { contestID } }">
          <el-icon><PictureFilled /></el-icon>
          {{ t('m.Problems') }}
        </VerticalMenuItem>
        <VerticalMenuItem v-if="OIContestRealTimePermission"
                          :disabled="contestMenuDisabled"
                          :route="{ name: 'contest-submission-list' }">
          <el-icon><List /></el-icon>
          {{ t('m.Submissions') }}
        </VerticalMenuItem>
        <VerticalMenuItem v-if="OIContestRealTimePermission"
                          :disabled="contestMenuDisabled"
                          :route="{ name: 'contest-rank', params: { contestID } }">
          <el-icon><TrendCharts /></el-icon>
          {{ t('m.Rankings') }}
        </VerticalMenuItem>
        <VerticalMenuItem v-if="showAdminHelper"
                          :route="{ name: 'acm-helper', params: { contestID } }">
          <el-icon><MagicStick /></el-icon>
          {{ t('m.Admin_Helper') }}
        </VerticalMenuItem>
      </VerticalMenu>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { House, ChatDotRound, PictureFilled, List, TrendCharts, MagicStick } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import api from '@oj/api'
import time from '@/utils/time'
import { CONTEST_STATUS_REVERSE, CONTEST_STATUS } from '@/utils/constants'
import VerticalMenu from '@oj/components/verticalMenu/verticalMenu.vue'
import VerticalMenuItem from '@oj/components/verticalMenu/verticalMenu-item.vue'
import { useContestStore } from '@/store/contest'
import { useAppStore } from '@/store/app'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const contestStore = useContestStore()
const appStore = useAppStore()

const route_name = ref('')
const contestID = ref('')
const contestPassword = ref('')
let timer = null

const contest = computed(() => contestStore.contest)
const contestTable = computed(() => [contestStore.contest])
const showMenu = computed(() => contestStore.itemVisible.menu)
const contestMenuDisabled = computed(() => contestStore.contestMenuDisabled)
const contestRuleType = computed(() => contestStore.contestRuleType)
const contestStatusVal = computed(() => contestStore.contestStatus)
const countdown = computed(() => contestStore.countdown)
const isContestAdmin = computed(() => contestStore.isContestAdmin)
const OIContestRealTimePermission = computed(() => contestStore.OIContestRealTimePermission)
const passwordFormVisible = computed(() => contestStore.passwordFormVisible)

const countdownType = computed(() => {
  if (!contestStatusVal.value) return 'warning'
  const color = CONTEST_STATUS_REVERSE[contestStatusVal.value]?.color
  if (color === 'green') return 'success'
  if (color === 'red') return 'danger'
  return 'warning'
})

const showAdminHelper = computed(() => isContestAdmin.value && contestRuleType.value === 'ACM')

function localtime (val) {
  return time.utcToLocal(val)
}

function handleRoute (routeObj) {
  router.push(routeObj)
}

function checkPassword () {
  if (contestPassword.value === '') {
    ElMessage.error("Password can't be empty")
    return
  }
  api.checkContestPassword(contestID.value, contestPassword.value).then(() => {
    ElMessage.success('Succeeded')
    contestStore.access = true
  }, () => {})
}

onMounted(() => {
  contestID.value = route.params.contestID
  route_name.value = route.name
  contestStore.getContest(contestID.value).then(res => {
    appStore.changeDomTitle(res.data.data.title)
    const data = res.data.data
    const endTime = dayjs(data.end_time)
    if (endTime.isAfter(dayjs(data.now))) {
      timer = setInterval(() => {
        contestStore.updateNow()
      }, 1000)
    }
  })
})

watch(() => route.fullPath, () => {
  route_name.value = route.name
  contestID.value = route.params.contestID
  appStore.changeDomTitle(contest.value.title)
})

onBeforeUnmount(() => {
  clearInterval(timer)
  contestStore.clearContest()
})
</script>

<style scoped lang="less">
  pre {
    display: inline-block;
  }

  #countdown {
    font-size: 16px;
  }

  .contest-info-table {
    margin-bottom: 40px;
  }

  .flex-container {
    #contest-main {
      flex: 1 1;
      width: 0;
      #contest-desc {
        flex: auto;
      }
    }
    #contest-menu {
      flex: none;
      width: 210px;
      margin-left: 20px;
    }
    .contest-password {
      margin-top: 20px;
      margin-bottom: -10px;
      &-input {
        width: 200px;
        margin-right: 10px;
      }
    }
  }
</style>
