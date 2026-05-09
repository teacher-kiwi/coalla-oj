<template>
  <el-row justify="space-around">
    <el-col :span="20" id="status">
      <el-alert :type="statusInfo.type === 'danger' ? 'error' : statusInfo.type" show-icon :closable="false">
        <template #title>
          <span class="title">{{ t('m.' + statusInfo.statusName.replace(/ /g, '_')) }}</span>
        </template>
        <div class="content">
          <template v-if="isCE">
            <pre>{{ submission.statistic_info.err_info }}</pre>
          </template>
          <template v-else>
            <span>{{ t('m.Time') }}: {{ submissionTimeFormat(submission.statistic_info.time_cost) }}</span>
            <span>{{ t('m.Memory') }}: {{ submissionMemoryFormat(submission.statistic_info.memory_cost) }}</span>
            <span>{{ t('m.Lang') }}: {{ submission.language }}</span>
            <span>{{ t('m.Author') }}: {{ submission.username }}</span>
          </template>
        </div>
      </el-alert>
    </el-col>

    <el-col v-if="submission.info && !isCE" :span="20">
      <el-table :data="submission.info.data" v-loading="loading" stripe>
        <el-table-column type="index" :label="t('m.ID')" align="center" />
        <el-table-column :label="t('m.Status')" align="center">
          <template #default="{ row }">
            <el-tag :type="JUDGE_STATUS[row.result].type">
              {{ t('m.' + JUDGE_STATUS[row.result].name.replace(/ /g, '_')) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('m.Memory')" align="center">
          <template #default="{ row }">{{ submissionMemoryFormat(row.memory) }}</template>
        </el-table-column>
        <el-table-column :label="t('m.Time')" align="center">
          <template #default="{ row }">{{ submissionTimeFormat(row.cpu_time) }}</template>
        </el-table-column>
        <el-table-column v-if="showScoreColumn" :label="t('m.Score')" align="center" prop="score" />
        <el-table-column v-if="isAdminRole" :label="t('m.Real_Time')" align="center">
          <template #default="{ row }">{{ submissionTimeFormat(row.real_time) }}</template>
        </el-table-column>
        <el-table-column v-if="isAdminRole" :label="t('m.Signal')" align="center" prop="signal" />
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
          {{ t('m.UnShare') }}
        </el-button>
        <el-button v-else type="primary" size="large" @click="shareSubmission(true)">
          {{ t('m.Share') }}
        </el-button>
      </div>
    </el-col>
  </el-row>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import api from '@oj/api'
import { JUDGE_STATUS } from '@/utils/constants'
import utils from '@/utils/utils'
import Highlight from '@oj/components/Highlight.vue'
import BlocklyViewer from '@oj/components/BlocklyViewer.vue'
import { useUserStore } from '@/store/user'

const { submissionTimeFormat, submissionMemoryFormat } = utils
const { t } = useI18n()
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
    ElMessage.success(t('m.Succeeded'))
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
