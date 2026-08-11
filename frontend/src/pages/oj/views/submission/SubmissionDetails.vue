<template>
  <el-row justify="space-around">
    <el-col :span="20" id="status">
      <el-alert :type="statusInfo.type === 'danger' ? 'error' : statusInfo.type" show-icon :closable="false">
        <template #title>
          <span class="title">{{ statusInfo.label }}</span>
        </template>
        <div class="content">
          <template v-if="isCE">
            <pre>{{ submission.statistic_info.err_info }}</pre>
          </template>
          <template v-else>
            <span>시간: {{ submissionTimeFormat(submission.statistic_info.time_cost) }}</span>
            <span>메모리: {{ submissionMemoryFormat(submission.statistic_info.memory_cost) }}</span>
            <span>언어: {{ submission.language }}</span>
            <span>작성자: {{ submission.username }}</span>
          </template>
        </div>
      </el-alert>
    </el-col>

    <el-col v-if="submission.info && !isCE" :span="20">
      <el-table :data="submission.info.data" v-loading="loading" stripe>
        <el-table-column type="index" label="ID" align="center" />
        <el-table-column label="상태" align="center">
          <template #default="{ row }">
            <el-tag :type="JUDGE_STATUS[row.result].type">
              {{ JUDGE_STATUS[row.result].label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="메모리" align="center">
          <template #default="{ row }">{{ submissionMemoryFormat(row.memory) }}</template>
        </el-table-column>
        <el-table-column label="시간" align="center">
          <template #default="{ row }">{{ submissionTimeFormat(row.cpu_time) }}</template>
        </el-table-column>
        <el-table-column v-if="showScoreColumn" label="점수" align="center" prop="score" />
        <el-table-column v-if="isAdminRole" label="실제 시간" align="center">
          <template #default="{ row }">{{ submissionTimeFormat(row.real_time) }}</template>
        </el-table-column>
        <el-table-column v-if="isAdminRole" label="시그널" align="center" prop="signal" />
      </el-table>
    </el-col>

    <el-col v-if="submission.language === 'Block Coding'" :span="20">
      <BlocklyViewer :blocks="submission.blockly_state" />
    </el-col>

    <el-col :span="20">
      <Highlight :code="submission.code" :language="highlightLanguage" :border-color="statusInfo.color" />
    </el-col>

    <el-col v-if="submission.can_unshare" :span="20">
      <div id="share-btn">
        <el-button v-if="submission.shared" type="warning" size="large" @click="shareSubmission(false)">
          공유 해제
        </el-button>
        <el-button v-else type="primary" size="large" @click="shareSubmission(true)">
          공유
        </el-button>
      </div>
    </el-col>
  </el-row>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '@oj/api'
import { JUDGE_STATUS } from '@/utils/constants'
import utils from '@/utils/utils'
import Highlight from '@oj/components/Highlight.vue'
import BlocklyViewer from '@oj/components/BlocklyViewer.vue'
import { useUserStore } from '@/store/user'

const { submissionTimeFormat, submissionMemoryFormat } = utils
const route = useRoute()
const userStore = useUserStore()

const loading = ref(false)
const showScoreColumn = ref(false)
const submission = ref({
  result: '0',
  code: '',
  info: { data: [] },
  statistic_info: { time_cost: '', memory_cost: '' }
})

const statusInfo = computed(() => ({
  type: JUDGE_STATUS[submission.value.result].type,
  statusName: JUDGE_STATUS[submission.value.result].name,
  label: JUDGE_STATUS[submission.value.result].label,
  color: JUDGE_STATUS[submission.value.result].color
}))

const isCE = computed(() => submission.value.result === -2)
const isAdminRole = computed(() => userStore.isAdminRole)
const highlightLanguage = computed(() =>
  submission.value.language === 'Block Coding' ? 'Python3' : submission.value.language
)

function getSubmission () {
  loading.value = true
  api.getSubmission(route.params.id).then(res => {
    loading.value = false
    const data = res.data.data
    if (data.info && data.info.data) {
      if (data.info.data[0]?.score !== undefined) {
        showScoreColumn.value = true
      }
    }
    submission.value = data
  }, () => {
    loading.value = false
  })
}

function shareSubmission (shared) {
  const data = { id: submission.value.id, shared }
  api.updateSubmission(data).then(() => {
    getSubmission()
    ElMessage.success('성공')
  }, () => {})
}

onMounted(() => {
  getSubmission()
})
</script>

<style scoped lang="less">
#status {
  .title {
    font-size: 20px;
  }
  .content {
    margin-top: 10px;
    font-size: 14px;
    span {
      margin-right: 10px;
    }
    pre {
      white-space: pre-wrap;
      word-wrap: break-word;
      word-break: break-all;
    }
  }
}

.admin-info {
  margin: 5px 0;
  &-content {
    font-size: 16px;
    padding: 10px;
  }
}

#share-btn {
  float: right;
  margin-top: 5px;
  margin-right: 10px;
}

pre {
  border: none;
  background: none;
}
</style>
