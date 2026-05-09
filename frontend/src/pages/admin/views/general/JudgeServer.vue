<template>
  <div class="view">
    <Panel :title="t('m.Judge_Server_Token')">
      <code>{{ token }}</code>
    </Panel>
    <Panel :title="t('m.Judge_Server_Info')">
      <el-table :data="servers" :default-expand-all="true" border>
        <el-table-column type="expand">
          <template #default="{ row }">
            <p>{{ t('m.IP') }}: <el-tag type="success">{{ row.ip }}</el-tag>&nbsp;&nbsp;
              {{ t('m.Judger_Version') }}: <el-tag type="success">{{ row.judger_version }}</el-tag></p>
            <p>{{ t('m.Service_URL') }}: <code>{{ row.service_url }}</code></p>
            <p>{{ t('m.Last_Heartbeat') }}: {{ localtime(row.last_heartbeat) }}</p>
            <p>{{ t('m.Create_Time') }}: {{ localtime(row.create_time) }}</p>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="Status">
          <template #default="{ row }">
            <el-tag :type="row.status === 'normal' ? 'success' : 'danger'">
              {{ row.status === 'normal' ? 'Normal' : 'Abnormal' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="hostname" label="Hostname" />
        <el-table-column prop="task_number" label="Task Number" />
        <el-table-column prop="cpu_core" label="CPU Core" />
        <el-table-column prop="cpu_usage" label="CPU Usage">
          <template #default="{ row }">{{ row.cpu_usage }}%</template>
        </el-table-column>
        <el-table-column prop="memory_usage" label="Memory Usage">
          <template #default="{ row }">{{ row.memory_usage }}%</template>
        </el-table-column>
        <el-table-column label="Disabled">
          <template #default="{ row }">
            <el-switch v-model="row.is_disabled" @change="handleDisabledSwitch(row.id, row.is_disabled)" />
          </template>
        </el-table-column>
        <el-table-column fixed="right" label="Options">
          <template #default="{ row }">
            <icon-btn name="Delete" icon="Delete" @click="deleteJudgeServer(row.hostname)" />
          </template>
        </el-table-column>
      </el-table>
    </Panel>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessageBox } from 'element-plus'
import api from '../../api.js'
import time from '@/utils/time'

const { t } = useI18n()

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
  ElMessageBox.confirm("If you delete this judge server, it can't be used until next heartbeat", 'Warning', {
    confirmButtonText: 'Delete', cancelButtonText: 'Cancel', type: 'warning'
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
