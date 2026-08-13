<template>
  <div>
    <Panel title="문제 내보내기 (베타)">
      <template #header>
        <el-input v-model="keyword" :prefix-icon="SearchIcon" placeholder="검색어" />
      </template>
      <el-table :data="problems" v-loading="loadingProblems" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="60" />
        <el-table-column label="ID" width="100" prop="id" />
        <el-table-column label="표시 ID" width="200" prop="_id" />
        <el-table-column label="제목" prop="title" />
        <el-table-column prop="created_by.username" label="작성자" />
        <el-table-column prop="create_time" label="생성 일시">
          <template #default="{ row }">{{ localtime(row.create_time) }}</template>
        </el-table-column>
      </el-table>
      <div class="panel-options">
        <el-button type="primary" size="small" v-show="selectedProblems.length" @click="exportProblems">내보내기</el-button>
        <el-pagination class="page" layout="prev, pager, next"
                       @current-change="getProblems" :page-size="limit" :total="total" />
      </div>
    </Panel>

    <Panel title="QDUOJ 문제 가져오기 (베타)">
      <el-upload ref="qduRef" action="/api/admin/import_problem" name="file"
                 :file-list="fileList1" :show-file-list="true" :with-credentials="true"
                 :limit="3" :on-change="onFile1Change" :auto-upload="false"
                 :on-success="uploadSucceeded" :on-error="uploadFailed">
        <template #trigger>
          <el-button size="small" type="primary">파일 선택</el-button>
        </template>
        <el-button class="upload-btn" size="small" type="success" @click="qduRef?.submit()">업로드</el-button>
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
const qduRef = ref(null)

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
function uploadSucceeded (response) {
  if (response.error) {
    ElMessage.error(response.data)
  } else {
    ElMessage.success('문제 ' + response.data.import_count + '개를 가져왔습니다')
    getProblems()
  }
}

function uploadFailed () { ElMessage.error('업로드에 실패했습니다') }

onMounted(() => { getProblems() })
watch(keyword, () => { getProblems() })
</script>

<style scoped>
.upload-btn {
  margin-left: 10px;
}
</style>
