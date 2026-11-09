<template>
  <div class="hw-home">
    <div v-if="loading" v-loading="true" class="placeholder"></div>

    <el-result v-else-if="notFound" icon="warning" title="과제를 찾을 수 없습니다"
               :sub-title="notFound">
      <template #extra>
        <el-button @click="router.push({ name: 'homework-entry' })">코드 다시 넣기</el-button>
      </template>
    </el-result>

    <template v-else-if="joined">
      <HomeworkHeader :homework="joined.homework" :participant="joined.participant" @leave="leave" />
      <el-alert v-if="joined.homework.ended" type="info" show-icon :closable="false" class="notice"
                title="종료된 과제입니다. 내 결과와 코드만 볼 수 있습니다" />
      <el-card class="problems">
        <div class="progress">
          <span class="progress-text">
            <b>{{ solvedCount }}</b> / {{ joined.homework.problems.length }} 문제 정답
          </span>
          <el-progress :percentage="progress" :show-text="false" :stroke-width="8"
                       status="success" class="progress-bar" />
        </div>
        <ul class="problem-list">
          <li v-for="(problem, index) in joined.homework.problems" :key="problem.id"
              :class="stateOf(problem)" @click="openProblem(problem)">
            <span class="no">
              <el-icon v-if="problem.solved"><Check /></el-icon>
              <template v-else>{{ index + 1 }}</template>
            </span>
            <span class="name">{{ problem.title }}</span>
            <span class="state">
              <template v-if="problem.solved">정답</template>
              <template v-else-if="problem.attempts">{{ problem.attempts }}번 냄 · 아직 못 맞힘</template>
              <template v-else>아직 안 냄</template>
            </span>
            <el-icon class="arrow"><ArrowRight /></el-icon>
          </li>
        </ul>
      </el-card>
    </template>

    <div v-else class="join">
      <el-card class="join-card">
        <p class="kicker">바로 과제 · {{ code }}</p>
        <h2>{{ info.title }}</h2>
        <el-alert v-if="info.ended" type="info" :closable="false" class="warn"
                  title="종료된 과제입니다. 이미 참가했다면 번호와 4자리 숫자로 내 결과를 볼 수 있습니다." />
        <el-alert v-else-if="info.entry_locked" type="warning" :closable="false" class="warn"
                  title="선생님이 새 입장을 막아 두었습니다. 이미 참가했다면 번호와 4자리 숫자로 다시 들어오세요." />
        <el-form label-position="top" @submit.prevent="join">
          <el-form-item label="번호">
            <el-input v-model="form.number" maxlength="5" inputmode="numeric"
                      placeholder="선생님이 정한 번호 (숫자 5자리까지)" />
          </el-form-item>
          <el-form-item label="닉네임">
            <el-input v-model="form.nickname" maxlength="20" placeholder="처음 들어올 때만 넣으면 됩니다" />
          </el-form-item>
          <el-form-item label="4자리 숫자">
            <el-input v-model="form.pin" maxlength="4" inputmode="numeric" placeholder="다시 들어올 때 필요합니다" />
            <p class="pin-hint">선생님께 보이는 숫자입니다. 쓰던 비밀번호는 넣지 마세요.</p>
          </el-form-item>
          <el-button type="primary" size="large" native-type="submit" :loading="joining" class="join-button">
            들어가기
          </el-button>
        </el-form>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Check, ArrowRight } from '@element-plus/icons-vue'
import api from '@oj/api'
import { useAppStore } from '@/store/app'
import HomeworkHeader from './HomeworkHeader.vue'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const code = route.params.code

const loading = ref(true)
const notFound = ref('')
// 입장 전에 보여 줄 제목·상태
const info = ref({})
// 입장한 뒤: { homework, participant }
const joined = ref(null)
const joining = ref(false)
const form = reactive({ number: '', nickname: '', pin: '' })

const solvedCount = computed(() => joined.value.homework.problems.filter(p => p.solved).length)
const progress = computed(() => {
  const total = joined.value.homework.problems.length
  return total ? Math.round(solvedCount.value / total * 100) : 0
})

function stateOf (problem) {
  if (problem.solved) return 'solved'
  return problem.attempts ? 'tried' : ''
}

function setJoined (data) {
  joined.value = data
  appStore.changeDomTitle(data.homework.title)
}

function loadInfo () {
  return api.getHomework(code).then(res => {
    info.value = res.data.data
    appStore.changeDomTitle(info.value.title)
  }, res => {
    notFound.value = res?.data?.data || '코드를 확인해주세요'
  })
}

function load () {
  loading.value = true
  api.getHomeworkMe(code).then(res => setJoined(res.data.data), res => {
    if (res?.data?.error === 'hw-join-required') return loadInfo()
    notFound.value = res?.data?.data || '코드를 확인해주세요'
  }).finally(() => { loading.value = false })
}

function join () {
  if (!/^\d{1,5}$/.test(form.number.trim())) {
    ElMessage.error('번호는 숫자 1~5자리로 넣어주세요')
    return
  }
  if (!/^\d{4}$/.test(form.pin.trim())) {
    ElMessage.error('4자리 숫자를 넣어주세요')
    return
  }
  joining.value = true
  api.joinHomework(code, { number: form.number.trim(), nickname: form.nickname, pin: form.pin.trim() })
    .then(res => setJoined(res.data.data), () => {})
    .finally(() => { joining.value = false })
}

function leave () {
  api.leaveHomework(code).then(() => {
    joined.value = null
    form.pin = ''
    loadInfo()
  }, () => {})
}

function openProblem (problem) {
  router.push({ name: 'homework-problem', params: { code, problemId: problem.id } })
}

onMounted(load)
</script>

<style lang="less" scoped>
// 바로 과제 화면은 모두 같은 폭을 쓴다. 목록에서 문제로 들어가도 상단 바가 움직이지 않는다.
.hw-home {
  max-width: 1000px;
  margin: 0 auto;
}
.placeholder {
  height: 200px;
}
.notice {
  margin-bottom: 16px;
}
.problems :deep(.el-card__body) {
  padding: 4px 20px 10px;
}
.progress {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 14px 8px;
  border-bottom: 1px solid #ebeef5;
  .progress-text {
    color: #606266;
    white-space: nowrap;
    b {
      font-size: 18px;
      color: var(--el-color-success);
    }
  }
  .progress-bar {
    flex: 1;
  }
}
.problem-list {
  list-style: none;
  margin: 0;
  padding: 0;
  li {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 14px 8px;
    border-bottom: 1px solid #ebeef5;
    cursor: pointer;
    transition: background-color .15s;
    &:last-child {
      border-bottom: none;
    }
    &:hover {
      background: #f5f7fa;
      .arrow {
        color: var(--el-color-primary);
      }
    }
  }
  // 번호 동그라미: 안 냄 = 회색 테두리, 냈지만 못 맞힘 = 주황, 정답 = 초록 체크
  .no {
    flex: none;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 30px;
    height: 30px;
    border-radius: 50%;
    border: 2px solid #dcdfe6;
    color: #909399;
    font-weight: 600;
    font-size: 14px;
  }
  .tried .no {
    border-color: var(--el-color-warning);
    color: var(--el-color-warning);
  }
  .solved .no {
    border-color: var(--el-color-success);
    background: var(--el-color-success);
    color: #fff;
  }
  .name {
    flex: 1;
    min-width: 0;
    font-size: 16px;
    color: #303133;
    overflow-wrap: anywhere;
  }
  .state {
    font-size: 13px;
    color: #909399;
    white-space: nowrap;
  }
  .tried .state {
    color: var(--el-color-warning);
  }
  .solved .state {
    color: var(--el-color-success);
    font-weight: 600;
  }
  .arrow {
    flex: none;
    color: #c0c4cc;
  }
}
.join {
  display: flex;
  justify-content: center;
  padding-top: 6vh;
}
.join-card {
  width: 100%;
  max-width: 420px;
  border-top: 4px solid var(--el-color-primary);
  :deep(.el-card__body) {
    padding: 28px;
  }
  .kicker {
    margin: 0;
    font-size: 13px;
    color: var(--el-color-primary);
    font-weight: 600;
  }
  h2 {
    margin: 4px 0 20px;
    overflow-wrap: anywhere;
  }
  .warn {
    margin: -6px 0 16px;
  }
  .pin-hint {
    margin: 4px 0 0;
    font-size: 12px;
    color: #909399;
    line-height: 1.4;
  }
  .join-button {
    width: 100%;
    margin-top: 4px;
  }
}
</style>
