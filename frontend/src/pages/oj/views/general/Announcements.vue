<template>
  <Panel shadow :padding="10">
    <template #title>{{ title }}</template>
    <template #extra>
      <el-button v-if="listVisible" type="info" :loading="btnLoading" @click="init">{{ t('m.Refresh') }}</el-button>
      <el-button v-else :icon="Back" @click="goBack">{{ t('m.Back') }}</el-button>
    </template>

    <transition-group name="announcement-animate">
      <div v-if="!announcements.length" class="no-announcement" key="no-announcement">
        <p>{{ t('m.No_Announcements') }}</p>
      </div>
      <template v-if="listVisible">
        <ul class="announcements-container" key="list">
          <li v-for="a in announcements" :key="a.title">
            <div class="flex-container">
              <div class="title">
                <a class="entry" @click="goAnnouncement(a)">{{ a.title }}</a>
              </div>
              <div class="date">{{ localtime(a.create_time) }}</div>
              <div class="creator"> {{ t('m.By') }} {{ a.created_by.username }}</div>
            </div>
          </li>
        </ul>
        <Pagination v-if="!isContest" :total="total" :page-size="limit" :current="page" @on-change="getAnnouncementList" />
      </template>
      <template v-else>
        <div v-katex v-html="announcement.content" key="content" class="content-container markdown-body"></div>
      </template>
    </transition-group>
  </Panel>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Back } from '@element-plus/icons-vue'
import api from '@oj/api'
import Pagination from '@oj/components/Pagination.vue'
import time from '@/utils/time'

const { t } = useI18n()
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
    return isContest.value ? t('m.Contest_Announcements') : t('m.Announcements')
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
          a.entry {
            color: #495060;
            cursor: pointer;
            &:hover {
              color: #2d8cf0;
              border-bottom: 1px solid #2d8cf0;
            }
          }
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
