<template>
  <el-row>
    <el-col :span="24">
      <Panel id="contest-card" shadow>
        <template #title>{{ query.rule_type === '' ? t('m.All') : query.rule_type }} {{ t('m.Contests') }}</template>
        <template #extra>
          <ul class="filter">
            <li>
              <el-dropdown @command="onRuleChange">
                <span class="el-dropdown-link">
                  {{ query.rule_type === '' ? t('m.Rule') : t('m.' + query.rule_type) }}
                  <el-icon><ArrowDown /></el-icon>
                </span>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="">{{ t('m.All') }}</el-dropdown-item>
                    <el-dropdown-item command="OI">{{ t('m.OI') }}</el-dropdown-item>
                    <el-dropdown-item command="ACM">{{ t('m.ACM') }}</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </li>
            <li>
              <el-dropdown @command="onStatusChange">
                <span class="el-dropdown-link">
                  {{ query.status === '' ? t('m.Status') : t('m.' + CONTEST_STATUS_REVERSE[query.status].name.replace(/ /g, '_')) }}
                  <el-icon><ArrowDown /></el-icon>
                </span>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="">{{ t('m.All') }}</el-dropdown-item>
                    <el-dropdown-item command="0">{{ t('m.Underway') }}</el-dropdown-item>
                    <el-dropdown-item command="1">{{ t('m.Not_Started') }}</el-dropdown-item>
                    <el-dropdown-item command="-1">{{ t('m.Ended') }}</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </li>
            <li>
              <el-input id="keyword" v-model="query.keyword" placeholder="Keyword" @keyup.enter="changeRoute">
                <template #suffix><el-icon><Search /></el-icon></template>
              </el-input>
            </li>
          </ul>
        </template>
        <p id="no-contest" v-if="contests.length === 0">{{ t('m.No_contest') }}</p>
        <ol id="contest-list">
          <li v-for="contest in contests" :key="contest.title">
            <el-row justify="space-between" align="middle">
              <img class="trophy" src="../../../../assets/Cup.png" />
              <el-col :span="18" class="contest-main">
                <p class="title">
                  <a class="entry" @click.stop="goContest(contest)">{{ contest.title }}</a>
                  <template v-if="contest.contest_type !== 'Public'">
                    <el-icon :size="20"><Lock /></el-icon>
                  </template>
                </p>
                <ul class="detail">
                  <li>
                    <el-icon color="#3091f2"><Calendar /></el-icon>
                    {{ localtime(contest.start_time) }}
                  </li>
                  <li>
                    <el-icon color="#3091f2"><Timer /></el-icon>
                    {{ getDuration(contest.start_time, contest.end_time) }}
                  </li>
                  <li>
                    <el-button size="small" round @click="onRuleChange(contest.rule_type)">
                      {{ contest.rule_type }}
                    </el-button>
                  </li>
                </ul>
              </el-col>
              <el-col :span="4" class="contest-status-col">
                <el-tag :type="getContestStatusType(contest.status)">
                  {{ t('m.' + CONTEST_STATUS_REVERSE[contest.status].name.replace(/ /g, '_')) }}
                </el-tag>
              </el-col>
            </el-row>
          </li>
        </ol>
      </Panel>
      <Pagination :total="total" :page-size="limit" :current="page"
                  @on-change="onPageChange" :show-sizer="true"
                  @on-page-size-change="onPageSizeChange" />
    </el-col>
  </el-row>
</template>

<script setup>
import { ref, reactive, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { ArrowDown, Search, Lock, Calendar, Timer } from '@element-plus/icons-vue'
import api from '@oj/api'
import utils from '@/utils/utils'
import time from '@/utils/time'
import Pagination from '@oj/components/Pagination.vue'
import { CONTEST_STATUS_REVERSE, CONTEST_TYPE } from '@/utils/constants'
import { useUserStore } from '@/store/user'
import { useAppStore } from '@/store/app'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const appStore = useAppStore()

const page = ref(1)
const limit = ref(10)
const total = ref(0)
const contests = ref([])
const query = reactive({ status: '', keyword: '', rule_type: '' })

function localtime (val) {
  return time.utcToLocal(val, 'YYYY-M-D HH:mm')
}

function getDuration (startTime, endTime) {
  return time.duration(startTime, endTime)
}

function getContestStatusType (status) {
  const color = CONTEST_STATUS_REVERSE[status]?.color
  if (color === 'green') return 'success'
  if (color === 'red') return 'danger'
  return 'warning'
}

function init () {
  const q = route.query
  query.status = q.status || ''
  query.rule_type = q.rule_type || ''
  query.keyword = q.keyword || ''
  page.value = parseInt(q.page) || 1
  limit.value = parseInt(q.limit) || 10
  getContestList(page.value)
}

function getContestList (p = 1) {
  const offset = (p - 1) * limit.value
  api.getContestList(offset, limit.value, query).then(res => {
    contests.value = res.data.data.results
    total.value = res.data.data.total
  })
}

function changeRoute () {
  const q = { ...query, page: page.value, limit: limit.value }
  router.push({ name: 'contest-list', query: utils.filterEmptyValue(q) })
}

function onRuleChange (rule) {
  query.rule_type = rule
  page.value = 1
  changeRoute()
}

function onStatusChange (status) {
  query.status = status
  page.value = 1
  changeRoute()
}

function onPageChange (newPage) {
  page.value = newPage
  changeRoute()
}

function onPageSizeChange (newSize) {
  limit.value = newSize
  page.value = 1
  changeRoute()
}

function goContest (contest) {
  if (contest.contest_type !== CONTEST_TYPE.PUBLIC && !userStore.isAuthenticated) {
    ElMessage.error(t('m.Please_login_first'))
    appStore.changeModalStatus({ visible: true })
  } else {
    router.push({ name: 'contest-details', params: { contestID: contest.id } })
  }
}

onMounted(() => {
  init()
})

watch(() => route.fullPath, (newVal, oldVal) => {
  if (newVal !== oldVal) init()
})
</script>

<style lang="less" scoped>
  #contest-card {
    #keyword {
      width: 80%;
      margin-right: 30px;
    }
    #no-contest {
      text-align: center;
      font-size: 16px;
      padding: 20px;
    }
    #contest-list {
      > li {
        padding: 20px;
        border-bottom: 1px solid rgba(187, 187, 187, 0.5);
        list-style: none;

        .trophy {
          height: 40px;
          margin-left: 10px;
          margin-right: -20px;
        }
        .contest-main {
          .title {
            font-size: 18px;
            a.entry {
              color: #495060;
              &:hover {
                color: #2d8cf0;
                border-bottom: 1px solid #2d8cf0;
              }
            }
          }
          li {
            display: inline-block;
            padding: 10px 0 0 10px;
            &:first-child {
              padding: 10px 0 0 0;
            }
          }
        }
      }
    }
  }
  .contest-status-col {
    text-align: center;
  }
</style>
