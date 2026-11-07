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
      <el-card>
        <ul class="problem-list">
          <li v-for="(problem, index) in joined.homework.problems" :key="problem.id"
              @click="openProblem(problem)">
            <span class="no">{{ index + 1 }}</span>
            <span class="name">{{ problem.title }}</span>
            <el-tag v-if="problem.solved" type="success">정답</el-tag>
            <el-tag v-else-if="problem.attempts" type="warning">{{ problem.attempts }}번 제출</el-tag>
            <el-tag v-else type="info" effect="plain">아직 안 냄</el-tag>
          </li>
        </ul>
      </el-card>
    </template>

    <div v-else class="join">
      <el-card class="join-card">
        <h2>{{ info.title }}</h2>
        <p v-if="info.ended" class="warn">
          종료된 과제입니다. 이미 참가했다면 번호와 4자리 숫자로 내 결과를 볼 수 있습니다.
        </p>
        <p v-else-if="info.entry_locked" class="warn">
          선생님이 새 입장을 막아 두었습니다. 이미 참가했다면 번호와 4자리 숫자로 다시 들어오세요.
        </p>
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
            <p class="pin-hint">선생님께 보이는 숫자입니다. 다른 곳에 쓰는 비밀번호를 넣지 마세요.</p>
          </el-form-item>
          <el-button type="primary" native-type="submit" :loading="joining" class="join-button">
            들어가기
          </el-button>
        </el-form>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
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
.hw-home {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px 0;
}
.placeholder {
  height: 200px;
}
.notice {
  margin-bottom: 16px;
}
.problem-list {
  list-style: none;
  margin: 0;
  padding: 0;
  li {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px 8px;
    border-bottom: 1px solid #ebeef5;
    cursor: pointer;
    &:last-child {
      border-bottom: none;
    }
    &:hover {
      background: #f5f7fa;
    }
  }
  .no {
    width: 24px;
    color: #909399;
    text-align: right;
  }
  .name {
    flex: 1;
    min-width: 0;
    overflow-wrap: anywhere;
  }
}
.join {
  display: flex;
  justify-content: center;
}
.join-card {
  width: 100%;
  max-width: 420px;
  h2 {
    margin: 0 0 12px;
    overflow-wrap: anywhere;
  }
  .warn {
    color: #e6a23c;
    margin: 0 0 12px;
  }
  .pin-hint {
    margin: 4px 0 0;
    font-size: 12px;
    color: #909399;
    line-height: 1.4;
  }
  .join-button {
    width: 100%;
  }
}
</style>
