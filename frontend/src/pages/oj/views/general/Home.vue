<template>
  <el-row type="flex" justify="space-around">
    <el-col :span="22">
      <Panel shadow :padding="10" v-if="contests.length" class="contest">
        <template #title>
          <el-button text class="contest-title" @click="goContest">
            {{ contests[index].title }}
          </el-button>
        </template>
        <el-carousel v-model="index" :interval="6000" height="300px">
          <el-carousel-item v-for="(contest, idx) of contests" :key="idx">
            <div class="contest-content">
              <div class="contest-content-tags">
                <el-button type="info" round size="small" :icon="Calendar">
                  {{ localtime(contest.start_time, 'YYYY-M-D HH:mm') }}
                </el-button>
                <el-button type="success" round size="small" :icon="Timer">
                  {{ getDuration(contest.start_time, contest.end_time) }}
                </el-button>
                <el-button type="warning" round size="small" :icon="Trophy">
                  {{ contest.rule_type }}
                </el-button>
              </div>
              <div class="contest-content-description">
                <blockquote v-html="contest.description"></blockquote>
              </div>
            </div>
          </el-carousel-item>
        </el-carousel>
      </Panel>
      <Announcements class="announcement" />
    </el-col>
  </el-row>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Calendar, Timer, Trophy } from '@element-plus/icons-vue'
import Announcements from './Announcements.vue'
import api from '@oj/api'
import time from '@/utils/time'
import { CONTEST_STATUS } from '@/utils/constants'

const router = useRouter()
const contests = ref([])
const index = ref(0)

function getDuration (startTime, endTime) {
  return time.duration(startTime, endTime)
}

function localtime (val, fmt) {
  return time.utcToLocal(val, fmt)
}

function goContest () {
  router.push({
    name: 'contest-details',
    params: { contestID: contests.value[index.value].id }
  })
}

onMounted(() => {
  api.getContestList(0, 5, { status: CONTEST_STATUS.NOT_START }).then((res) => {
    contests.value = res.data.data.results
  })
})
</script>

<style lang="less" scoped>
  .contest {
    &-title {
      font-style: italic;
      font-size: 21px;
    }
    &-content {
      padding: 0 70px 40px 70px;
      &-description {
        margin-top: 25px;
      }
    }
  }

  .announcement {
    margin-top: 20px;
  }
</style>
