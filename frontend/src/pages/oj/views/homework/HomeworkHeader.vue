<template>
  <div class="hw-header">
    <router-link :to="{ name: 'homework-home', params: { code: homework.code } }" class="hw-title">
      <span class="kicker">바로 과제 · {{ homework.code }}</span>
      <span class="title">{{ homework.title }}</span>
    </router-link>

    <div class="hw-side">
      <!-- 학생에게 가장 중요한 정보라 크게 둔다. 10분 아래로 남으면 주황, 끝나면 회색 -->
      <div :class="['clock', clockState]">
        <span class="left">{{ clock.left }}</span>
        <span v-if="clock.until" class="until">{{ clock.until }}</span>
      </div>
      <div v-if="participant" class="hw-me">
        <span class="me">{{ participant.number }}번 {{ participant.nickname }}</span>
        <el-button size="small" @click="leave">나가기</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessageBox } from 'element-plus'
import time from '@/utils/time'

const props = defineProps({
  homework: { type: Object, required: true },
  participant: { type: Object, default: null }
})
const emit = defineEmits(['leave'])

// 남은 시간은 분 단위로 충분하다. 30초마다 다시 센다.
const nowMs = ref(Date.now())
let timer = null
onMounted(() => { timer = setInterval(() => { nowMs.value = Date.now() }, 30 * 1000) })
onBeforeUnmount(() => clearInterval(timer))

const minutesLeft = computed(() =>
  Math.ceil((new Date(props.homework.end_time).getTime() - nowMs.value) / 60000))

const clock = computed(() => {
  if (props.homework.ended) return { left: '종료됨', until: '' }
  // 화면을 켜 둔 채 마감이 지났다. 제출은 서버가 막는다.
  if (minutesLeft.value <= 0) return { left: '마감', until: '' }
  const minutes = minutesLeft.value
  const until = time.utcToLocal(props.homework.end_time, minutes < 60 * 24 ? 'HH:mm 마감' : 'M/D HH:mm 마감')
  if (minutes < 60) return { left: `${minutes}분 남음`, until }
  if (minutes < 60 * 24) return { left: `${Math.floor(minutes / 60)}시간 ${minutes % 60}분 남음`, until }
  return { left: `${Math.floor(minutes / 60 / 24)}일 남음`, until }
})

const clockState = computed(() => {
  if (props.homework.ended || minutesLeft.value <= 0) return 'over'
  return minutesLeft.value <= 10 ? 'soon' : ''
})

function leave () {
  ElMessageBox.confirm('이 기기에서 나갑니다. 번호와 4자리 숫자로 다시 들어올 수 있습니다.', '나가기')
    .then(() => emit('leave')).catch(() => {})
}
</script>

<style lang="less" scoped>
.hw-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px 24px;
  margin-bottom: 16px;
  padding: 14px 20px;
  background: #fff;
  border-radius: 8px;
  border-top: 4px solid var(--el-color-primary);
  box-shadow: var(--el-box-shadow-light);
}
.hw-title {
  display: flex;
  flex-direction: column;
  min-width: 0;
  color: inherit;
  text-decoration: none;
  .kicker {
    font-size: 12px;
    color: #909399;
    letter-spacing: 0.5px;
  }
  .title {
    font-size: 20px;
    font-weight: 600;
    color: #303133;
    overflow-wrap: anywhere;
  }
}
.hw-side {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px 20px;
}
.clock {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  line-height: 1.3;
  .left {
    font-size: 20px;
    font-weight: 700;
    color: var(--el-color-success);
  }
  .until {
    font-size: 12px;
    color: #909399;
  }
  &.soon .left {
    color: var(--el-color-warning);
  }
  &.over .left {
    color: #909399;
  }
}
.hw-me {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-left: 20px;
  border-left: 1px solid #ebeef5;
  .me {
    color: #606266;
  }
}
</style>
