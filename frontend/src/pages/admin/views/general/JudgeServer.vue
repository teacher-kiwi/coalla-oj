<template>
  <div class="view">
    <Panel title="채점 서버 토큰">
      <code>{{ token }}</code>
    </Panel>
    <Panel title="채점 서버">
      <el-table :data="servers" :default-expand-all="true" border>
        <el-table-column type="expand">
          <template #default="{ row }">
            <p>IP: <el-tag type="success">{{ row.ip }}</el-tag>&nbsp;&nbsp;
              채점기 버전: <el-tag type="success">{{ row.judger_version }}</el-tag></p>
            <p>서비스 URL: <code>{{ row.service_url }}</code></p>
            <p>마지막 하트비트: {{ localtime(row.last_heartbeat) }}</p>
            <p>생성 시간: {{ localtime(row.create_time) }}</p>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="상태">
          <template #default="{ row }">
            <el-tag :type="row.status === 'normal' ? 'success' : 'danger'">
              {{ row.status === 'normal' ? 'Normal' : 'Abnormal' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="hostname" label="호스트명" />
        <el-table-column prop="task_number" label="작업 수" />
        <el-table-column prop="cpu_core" label="CPU 코어" />
        <el-table-column prop="cpu_usage" label="CPU 사용률">
          <template #default="{ row }">{{ row.cpu_usage }}%</template>
        </el-table-column>
        <el-table-column prop="memory_usage" label="메모리 사용률">
          <template #default="{ row }">{{ row.memory_usage }}%</template>
        </el-table-column>
        <el-table-column label="비활성화">
          <template #default="{ row }">
            <el-switch v-model="row.is_disabled" @change="handleDisabledSwitch(row.id, row.is_disabled)" />
          </template>
        </el-table-column>
        <el-table-column fixed="right" label="옵션">
          <template #default="{ row }">
            <icon-btn name="삭제" icon="Delete" @click="deleteJudgeServer(row.hostname)" />
          </template>
        </el-table-column>
      </el-table>
    </Panel>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import api from '../../api.js'
import time from '@/utils/time'

const servers = ref([])
const token = ref('')
let intervalId = -1

function localtime (val) { return time.utcToLocal(val) }

function refreshJudgeServerList () {
  api.getJudgeServer().then(res => {
    servers.value = res.data.data.servers
    token.value = res.data.data.token
  })
}

function deleteJudgeServer (hostname) {
  ElMessageBox.confirm('채점 서버를 삭제하면 다음 하트비트 전까지 사용할 수 없습니다', '경고', {
    confirmButtonText: '삭제', cancelButtonText: '취소', type: 'warning'
  }).then(() => {
    api.deleteJudgeServer(hostname).then(() => refreshJudgeServerList())
  }).catch(() => {})
}

function handleDisabledSwitch (id, value) {
  api.updateJudgeServer({ id, is_disabled: value }).catch(() => {})
}

onMounted(() => {
  refreshJudgeServerList()
  intervalId = setInterval(() => refreshJudgeServerList(), 5000)
})

onBeforeRouteLeave(() => {
  clearInterval(intervalId)
})
</script>
