<template>
  <el-row type="flex" justify="space-around">
    <el-col :span="22">
      <el-card shadow="never" class="homework-entry">
        <form @submit.prevent="goHomework">
          <span class="homework-label">바로 과제</span>
          <el-input v-model="homeworkCode" maxlength="6" inputmode="numeric"
                    placeholder="선생님께 받은 6자리 숫자" class="homework-code" />
          <el-button type="primary" native-type="submit">들어가기</el-button>
        </form>
      </el-card>
      <Panel shadow :padding="10" v-if="contests.length" class="contest">
        <template #title>
          <el-button text class="contest-title" @click="goContest">
            {{ contests[index].title }}
          </el-button>
        </template>
        <!-- el-carousel 은 v-model 을 지원하지 않는다(modelValue prop 이 없다).
             현재 위치는 change 이벤트로만 알 수 있어, 이걸 놓치면 제목과
             "대회 열기" 링크가 첫 대회에 멈춘다. -->
        <el-carousel :interval="6000" height="300px" @change="onCarouselChange">
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
                <Markdown :source="contest.description" />
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
import Markdown from '@oj/components/Markdown.vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Calendar, Timer, Trophy } from '@element-plus/icons-vue'
import Announcements from './Announcements.vue'
import api from '@oj/api'
import time from '@/utils/time'
import { CONTEST_STATUS } from '@/utils/constants'

const router = useRouter()
const contests = ref([])
const homeworkCode = ref('')

function goHomework () {
  const code = homeworkCode.value.trim()
  if (!/^\d{6}$/.test(code)) {
    ElMessage.error('6자리 숫자를 넣어주세요')
    return
  }
  router.push({ name: 'homework-home', params: { code } })
}
const index = ref(0)

function onCarouselChange (newIndex) {
  index.value = newIndex
}

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
  .homework-entry {
    margin-bottom: 20px;
    form {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 10px;
    }
    .homework-label {
      font-weight: 600;
    }
    .homework-code {
      flex: 1 1 180px;
      max-width: 260px;
    }
  }
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
