<template>
  <div>
    <Panel title="Export Problems (beta)">
      <template #header>
        <el-input v-model="keyword" :prefix-icon="SearchIcon" placeholder="Keywords" />
      </template>
      <el-table :data="problems" v-loading="loadingProblems" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="60" />
        <el-table-column label="ID" width="100" prop="id" />
        <el-table-column label="DisplayID" width="200" prop="_id" />
        <el-table-column label="Title" prop="title" />
        <el-table-column prop="created_by.username" label="Author" />
        <el-table-column prop="create_time" label="Create Time">
          <template #default="{ row }">{{ localtime(row.create_time) }}</template>
        </el-table-column>
      </el-table>
      <div class="panel-options">
        <el-button type="primary" size="small" v-show="selectedProblems.length" @click="exportProblems">Export</el-button>
        <el-pagination class="page" layout="prev, pager, next"
                       @current-change="getProblems" :page-size="limit" :total="total" />
      </div>
    </Panel>

    <Panel title="Import QDUOJ Problems (beta)">
      <el-upload ref="qduRef" action="/api/admin/import_problem" name="file"
                 :file-list="fileList1" :show-file-list="true" :with-credentials="true"
                 :limit="3" :on-change="onFile1Change" :auto-upload="false"
                 :on-success="uploadSucceeded" :on-error="uploadFailed">
        <template #trigger>
          <el-button size="small" type="primary">Choose File</el-button>
        </template>
        <el-button class="upload-btn" size="small" type="success" @click="qduRef?.submit()">Upload</el-button>
      </el-upload>
    </Panel>

    <Panel title="Import FPS Problems (beta)">
      <el-upload ref="fpsRef" action="/api/admin/import_fps" name="file"
                 :file-list="fileList2" :show-file-list="true" :with-credentials="true"
                 :limit="3" :on-change="onFile2Change" :auto-upload="false"
                 :on-success="uploadSucceeded" :on-error="uploadFailed">
        <template #trigger>
          <el-button size="small" type="primary">Choose File</el-button>
        </template>
        <el-button class="upload-btn" size="small" type="success" @click="fpsRef?.submit()">Upload</el-button>
      </el-upload>
    </Panel>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { Search as SearchIcon } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import api from '@admin/api'
import utils from '@/utils/utils'
import time from '@/utils/time'

const limit = 10
const total = ref(0)
const loadingProblems = ref(false)
const keyword = ref('')
const problems = ref([])
const selectedProblems = ref([])
const fileList1 = ref([])
const fileList2 = ref([])
const qduRef = ref(null)
const fpsRef = ref(null)

function localtime (val) { return time.utcToLocal(val) }

function handleSelectionChange (val) { selectedProblems.value = val }

function getProblems (page = 1) {
  loadingProblems.value = true
  api.getProblemList({ keyword: keyword.value, offset: (page - 1) * limit, limit }).then(res => {
    problems.value = res.data.data.results
    total.value = res.data.data.total
    loadingProblems.value = false
  })
}

function exportProblems () {
  const params = selectedProblems.value.map(p => 'problem_id=' + p.id)
  utils.downloadFile('/admin/export_problem?' + params.join('&'))
}

function onFile1Change (file, fileList) { fileList1.value = fileList.slice(-1) }
function onFile2Change (file, fileList) { fileList2.value = fileList.slice(-1) }

function uploadSucceeded (response) {
  if (response.error) {
    ElMessage.error(response.data)
  } else {
    ElMessage.success('Successfully imported ' + response.data.import_count + ' problems')
    getProblems()
  }
}

function uploadFailed () { ElMessage.error('Upload failed') }

onMounted(() => { getProblems() })
watch(keyword, () => { getProblems() })
</script>

<style scoped>
.upload-btn {
  margin-left: 10px;
}
</style>
