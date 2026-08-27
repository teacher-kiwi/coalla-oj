<template>
  <el-row>
    <el-col :span="24">
      <Panel id="contest-card" shadow>
        <template #title>{{ query.rule_type === '' ? '전체' : query.rule_type }} 대회</template>
        <template #extra>
          <ul class="filter">
            <li>
              <!-- 공개 대회와 학급 대회는 성격이 달라 섞이면 학생이 헷갈린다 -->
              <el-dropdown @command="onScopeChange">
                <span class="el-dropdown-link">
                  {{ query.scope === '' ? '범위' : SCOPE_LABEL[query.scope] }}
                  <el-icon><ArrowDown /></el-icon>
                </span>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="">전체</el-dropdown-item>
                    <el-dropdown-item command="class">학급</el-dropdown-item>
                    <el-dropdown-item command="public">공개</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </li>
            <li>
              <el-dropdown @command="onRuleChange">
                <span class="el-dropdown-link">
                  {{ query.rule_type === '' ? '규칙' : RULE_TYPE_LABEL[query.rule_type] }}
                  <el-icon><ArrowDown /></el-icon>
                </span>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="">전체</el-dropdown-item>
                    <el-dropdown-item command="OI">OI</el-dropdown-item>
                    <el-dropdown-item command="ACM">ACM</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </li>
            <li>
              <el-dropdown @command="onStatusChange">
                <span class="el-dropdown-link">
                  {{ query.status === '' ? '상태' : CONTEST_STATUS_REVERSE[query.status].label }}
                  <el-icon><ArrowDown /></el-icon>
                </span>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="">전체</el-dropdown-item>
                    <el-dropdown-item command="0">진행 중</el-dropdown-item>
                    <el-dropdown-item command="1">시작 전</el-dropdown-item>
                    <el-dropdown-item command="-1">종료</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </li>
            <li>
              <el-input id="keyword" v-model="query.keyword" placeholder="검색어" @keyup.enter="changeRoute">
                <template #suffix><el-icon><Search /></el-icon></template>
              </el-input>
            </li>
          </ul>
        </template>
        <p id="no-contest" v-if="contests.length === 0">대회 없음</p>
        <ol id="contest-list">
          <li v-for="contest in contests" :key="contest.title">
            <el-row justify="space-between" align="middle">
              <img class="trophy" :src="contest.is_class_contest ? lectureIcon : cupIcon"
                   :alt="contest.is_class_contest ? '학급 대회' : '공개 대회'" />
              <el-col :span="18" class="contest-main">
                <p class="title">
                  <a class="entry" @click.stop="goContest(contest)">{{ contest.title }}</a>
                  <el-tag v-if="contest.is_class_contest" type="success" size="small"
                          effect="plain" class="kind">학급</el-tag>
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
                  {{ CONTEST_STATUS_REVERSE[contest.status].label }}
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
import { ElMessage } from 'element-plus'
import { ArrowDown, Search, Lock, Calendar, Timer } from '@element-plus/icons-vue'
import api from '@oj/api'
import utils from '@/utils/utils'
import time from '@/utils/time'
import Pagination from '@oj/components/Pagination.vue'
// 학급 대회는 수업의 연장이라 트로피 대신 수업 아이콘을 쓴다
import cupIcon from '@/assets/Cup.png'
import lectureIcon from '@/assets/Lecture.png'
import { CONTEST_STATUS_REVERSE, CONTEST_TYPE, RULE_TYPE_LABEL } from '@/utils/constants'

// 학급 대회(교사가 자기 학급에 배포)와 공개 대회(관리자)를 나눠 본다
const SCOPE_LABEL = { class: '학급', public: '공개' }
import { useUserStore } from '@/store/user'
import { useAppStore } from '@/store/app'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const appStore = useAppStore()

const page = ref(1)
const limit = ref(10)
const total = ref(0)
const contests = ref([])
const query = reactive({ status: '', keyword: '', rule_type: '', scope: '' })

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
  query.scope = q.scope || ''
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

function onScopeChange (scope) {
  query.scope = scope
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
    ElMessage.error('먼저 로그인하세요!')
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

.kind {
  margin-left: 8px;
  vertical-align: 3px;
}
</style>
