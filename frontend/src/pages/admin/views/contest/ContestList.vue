<template>
  <div class="view">
    <Panel title="Contest List">
      <template #header>
        <el-input v-model="keyword" :prefix-icon="SearchIcon" placeholder="Keywords" />
      </template>
      <el-table v-loading="loading" :data="contestList" class="full-width">
        <el-table-column type="expand">
          <template #default="{ row }">
            <p>Start Time: {{ localtime(row.start_time) }}</p>
            <p>End Time: {{ localtime(row.end_time) }}</p>
            <p>Create Time: {{ localtime(row.create_time) }}</p>
            <p>Creator: {{ row.created_by.username }}</p>
          </template>
        </el-table-column>
        <el-table-column prop="id" width="80" label="ID" />
        <el-table-column prop="title" label="Title" />
        <el-table-column label="Rule Type" width="130">
          <template #default="{ row }">
            <el-tag type="info">{{ row.rule_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Contest Type" width="180">
          <template #default="{ row }">
            <el-tag :type="row.contest_type === 'Public' ? 'success' : 'primary'">{{ row.contest_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Status" width="130">
          <template #default="{ row }">
            <el-tag :type="row.status === '-1' ? 'danger' : row.status === '0' ? 'success' : 'primary'">
              {{ contestStatus(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column width="100" label="Visible">
          <template #default="{ row }">
            <el-switch v-model="row.visible" @change="handleVisibleSwitch(row)" />
          </template>
        </el-table-column>
        <el-table-column fixed="right" width="250" label="Operation">
          <template #default="{ row }">
            <icon-btn name="Edit" icon="Edit" @click="goEdit(row.id)" />
            <icon-btn name="Problem" icon="List" @click="goContestProblemList(row.id)" />
            <icon-btn name="Announcement" icon="InfoFilled" @click="goContestAnnouncement(row.id)" />
            <icon-btn icon="Download" name="Download Accepted Submissions" @click="openDownloadOptions(row.id)" />
          </template>
        </el-table-column>
      </el-table>
      <div class="panel-options">
        <el-pagination class="page" layout="prev, pager, next"
                       @current-change="currentChange" :page-size="pageSize" :total="total" />
      </div>
    </Panel>

    <el-dialog title="Download Contest Submissions" width="30%" v-model="downloadDialogVisible">
      <el-switch v-model="excludeAdmin" active-text="Exclude admin submissions" />
      <template #footer>
        <el-button type="primary" @click="downloadSubmissions">Download</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search as SearchIcon } from '@element-plus/icons-vue'
import api from '../../api.js'
import utils from '@/utils/utils'
import time from '@/utils/time'
import { CONTEST_STATUS_REVERSE } from '@/utils/constants'

const router = useRouter()

const pageSize = 10
const total = ref(0)
const contestList = ref([])
const keyword = ref('')
const loading = ref(false)
const excludeAdmin = ref(true)
const currentPage = ref(1)
const currentId = ref(1)
const downloadDialogVisible = ref(false)

function localtime (val) { return time.utcToLocal(val) }
function contestStatus (value) { return CONTEST_STATUS_REVERSE[value].name }

function currentChange (page) {
  currentPage.value = page
  getContestList(page)
}

function getContestList (page) {
  loading.value = true
  api.getContestList((page - 1) * pageSize, pageSize, keyword.value).then(res => {
    loading.value = false
    total.value = res.data.data.total
    contestList.value = res.data.data.results
  }, () => { loading.value = false })
}

function openDownloadOptions (contestId) {
  downloadDialogVisible.value = true
  currentId.value = contestId
}

function downloadSubmissions () {
  const exclude = excludeAdmin.value ? '1' : '0'
  utils.downloadFile(`/admin/download_submissions?contest_id=${currentId.value}&exclude_admin=${exclude}`)
}

function goEdit (contestId) { router.push({ name: 'edit-contest', params: { contestId } }) }
function goContestAnnouncement (contestId) { router.push({ name: 'contest-announcement', params: { contestId } }) }
function goContestProblemList (contestId) { router.push({ name: 'contest-problem-list', params: { contestId } }) }
function handleVisibleSwitch (row) { api.editContest(row) }

onMounted(() => { getContestList(1) })
watch(keyword, () => { currentChange(1) })
</script>

<style scoped>
.full-width {
  width: 100%;
}
</style>
