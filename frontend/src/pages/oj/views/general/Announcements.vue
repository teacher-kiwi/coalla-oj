<template>
  <Panel shadow :padding="10">
    <template #title>{{ title }}</template>
    <template #extra>
      <el-button v-if="listVisible" type="info" :loading="btnLoading" @click="init">새로고침</el-button>
      <el-button v-else :icon="Back" @click="goBack">뒤로</el-button>
    </template>

    <transition-group name="announcement-animate">
      <div v-if="!announcements.length" class="no-announcement" key="no-announcement">
        <p>공지 없음</p>
      </div>
      <template v-if="listVisible">
        <ul class="announcements-container" key="list">
          <li v-for="a in announcements" :key="a.title">
            <div class="flex-container">
              <div class="title">
                <a class="link-text" @click="goAnnouncement(a)">{{ a.title }}</a>
              </div>
              <div class="date">{{ localtime(a.create_time) }}</div>
              <div class="creator"> 작성자 {{ a.created_by.username }}</div>
            </div>
          </li>
        </ul>
        <Pagination v-if="!isContest" :total="total" :page-size="limit" :current="page" @on-change="getAnnouncementList" />
      </template>
      <template v-else>
        <Markdown :source="announcement.content" key="content" class="content-container" />
      </template>
    </transition-group>
  </Panel>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import Markdown from '@oj/components/Markdown.vue'
import { useRoute } from 'vue-router'
import { Back } from '@element-plus/icons-vue'
import api from '@oj/api'
import Pagination from '@oj/components/Pagination.vue'
import time from '@/utils/time'
const route = useRoute()

const limit = 10
const total = ref(0)
const page = ref(1)
const btnLoading = ref(false)
const announcements = ref([])
const announcement = ref({})
const listVisible = ref(true)

const isContest = computed(() => !!route.params.contestID)
const title = computed(() => {
  if (listVisible.value) {
    return isContest.value ? '대회 공지' : '공지'
  }
  return announcement.value.title
})

function localtime (val) {
  return time.utcToLocal(val)
}

function getAnnouncementList (p = 1) {
  page.value = p
  btnLoading.value = true
  api.getAnnouncementList((p - 1) * limit, limit).then((res) => {
    btnLoading.value = false
    announcements.value = res.data.data.results
    total.value = res.data.data.total
  }, () => {
    btnLoading.value = false
  })
}

function getContestAnnouncementList () {
  btnLoading.value = true
  api.getContestAnnouncementList(route.params.contestID).then((res) => {
    btnLoading.value = false
    announcements.value = res.data.data
  }, () => {
    btnLoading.value = false
  })
}

function init () {
  if (isContest.value) {
    getContestAnnouncementList()
  } else {
    getAnnouncementList()
  }
}

function goAnnouncement (a) {
  announcement.value = a
  listVisible.value = false
}

function goBack () {
  listVisible.value = true
  announcement.value = {}
}

onMounted(init)
</script>

<style scoped lang="less">
  .announcements-container {
    margin-top: -10px;
    margin-bottom: 10px;
    // 목록 기본값인 왼쪽 40px 을 지운다. li 에 list-style: none 을 주어 기호를
    // 없앴으므로 그 자리는 빈 들여쓰기로만 남는다(들여쓰기는 li 가 정한다).
    padding: 0;
    li {
      padding-top: 15px;
      list-style: none;
      padding-bottom: 15px;
      margin-left: 20px;
      font-size: 16px;
      border-bottom: 1px solid rgba(187, 187, 187, 0.5);
      &:last-child {
        border-bottom: none;
      }
      .flex-container {
        display: flex;
        .title {
          flex: 1 1;
          text-align: left;
          padding-left: 10px;
        }
        .creator {
          flex: none;
          width: 200px;
          text-align: center;
        }
        .date {
          flex: none;
          width: 200px;
          text-align: center;
        }
      }
    }
  }

  .content-container {
    padding: 0 20px 20px 20px;
  }

  .no-announcement {
    text-align: center;
    font-size: 16px;
  }

  .announcement-animate-enter-active {
    animation: fadeIn 1s;
  }
</style>
