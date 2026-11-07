<template>
  <div class="hw-header">
    <div class="hw-title">
      <router-link :to="{ name: 'homework-home', params: { code: homework.code } }" class="title">
        {{ homework.title }}
      </router-link>
      <el-tag v-if="homework.ended" type="info" effect="plain">종료</el-tag>
      <el-tag v-else type="success" effect="plain">{{ remaining }}</el-tag>
    </div>
    <div v-if="participant" class="hw-me">
      <span class="me">{{ participant.number }}번 {{ participant.nickname }}</span>
      <el-button size="small" @click="leave">나가기</el-button>
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

const remaining = computed(() => {
  const left = new Date(props.homework.end_time).getTime() - nowMs.value
  // 화면을 켜 둔 채 마감이 지났다. 제출은 서버가 막는다.
  if (left <= 0) return '마감'
  const minutes = Math.ceil(left / 60000)
  const until = time.utcToLocal(props.homework.end_time, 'M/D HH:mm')
  if (minutes < 60) return `${minutes}분 남음 (${until} 마감)`
  if (minutes < 60 * 24) return `${Math.floor(minutes / 60)}시간 ${minutes % 60}분 남음 (${until} 마감)`
  return `${until} 마감`
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
  gap: 8px 16px;
  margin-bottom: 16px;
}
.hw-title {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  .title {
    font-size: 20px;
    font-weight: 600;
    color: inherit;
    text-decoration: none;
    overflow-wrap: anywhere;
  }
}
.hw-me {
  display: flex;
  align-items: center;
  gap: 10px;
  .me {
    color: #606266;
  }
}
</style>
