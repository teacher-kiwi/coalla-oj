<template>
  <div class="view">
    <Panel :title="contestId ? '대회 문제 목록' : '문제 목록'">
      <template #header>
        <el-input v-model="keyword" :prefix-icon="SearchIcon" placeholder="검색어" />
      </template>
      <el-table v-loading="loading" :data="problemList" @row-dblclick="handleDblclick" class="full-width">
        <el-table-column width="100" prop="id" label="ID" />
        <el-table-column width="150" label="표시 ID">
          <template #default="{ row }">
            <span v-show="!row.isEditing">{{ row._id }}</span>
            <el-input v-show="row.isEditing" v-model="row._id" @keyup.enter="handleInlineEdit(row)" />
          </template>
        </el-table-column>
        <el-table-column prop="title" label="제목">
          <template #default="{ row }">
            <span v-show="!row.isEditing">{{ row.title }}</span>
            <el-input v-show="row.isEditing" v-model="row.title" @keyup.enter="handleInlineEdit(row)" />
          </template>
        </el-table-column>
        <el-table-column prop="created_by.username" label="작성자" />
        <el-table-column width="200" prop="create_time" label="생성 일시">
          <template #default="{ row }">{{ localtime(row.create_time) }}</template>
        </el-table-column>
        <!-- "공개" 는 학생 문제 목록에 나오는지를 뜻한다.
             교사가 만든 문제는 공개 승인 전까지 학생에게 보이지 않으므로,
             스위치를 꺼진 상태로 잠가 실제와 어긋나지 않게 한다.
             (DB 의 visible 은 True 라서 그대로 보여주면 "공개"로 읽힌다) -->
        <el-table-column width="130" label="공개">
          <template #default="{ row }">
            <el-switch v-if="row.visibility === 'public'" v-model="row.visible"
                       @change="updateProblem(row)" />
            <template v-else>
              <el-tooltip :content="lockedReason(row)" placement="top">
                <el-switch :model-value="false" disabled />
              </el-tooltip>
              <el-tag v-if="row.visibility === 'pending'" size="small" type="warning"
                      class="state-tag">승인 대기</el-tag>
            </template>
          </template>
        </el-table-column>
        <el-table-column fixed="right" label="관리" width="250">
          <template #default="{ row }">
            <icon-btn name="수정" icon="Edit" @click="goEdit(row.id)" />
            <icon-btn v-if="contestId" name="공개로 전환" icon="CopyDocument" @click="makeContestProblemPublic(row.id)" />
            <icon-btn icon="Download" name="테스트 케이스 내려받기" @click="downloadTestCase(row.id)" />
            <icon-btn icon="Delete" name="문제 삭제" @click="deleteProblem(row.id)" />
          </template>
        </el-table-column>
      </el-table>
      <div class="panel-options">
        <el-button type="primary" size="small" @click="goCreateProblem" :icon="Plus">생성</el-button>
        <el-button v-if="contestId" type="primary" size="small" :icon="Plus"
                   @click="addProblemDialogVisible = true">공개 문제에서 추가</el-button>
        <el-pagination class="page" layout="prev, pager, next"
                       @current-change="currentChange" :page-size="pageSize" :total="total" />
      </div>
    </Panel>

    <el-dialog title="문제를 수정하시겠습니까?" width="20%" v-model="inlineEditDialogVisible"
               :close-on-click-modal="false">
      <div>
        <p>DisplayID: {{ currentRow._id }}</p>
        <p>Title: {{ currentRow.title }}</p>
      </div>
      <template #footer>
        <cancel @click="inlineEditDialogVisible = false; getProblemList(currentPage)" />
        <save @click="updateProblem(currentRow)" />
      </template>
    </el-dialog>

    <el-dialog v-if="contestId" title="대회 문제 추가" width="80%" v-model="addProblemDialogVisible"
               :close-on-click-modal="false">
      <AddProblemComponent :contestID="contestId" @on-change="getProblemList" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { Plus, Search as SearchIcon } from '@element-plus/icons-vue'
import AddProblemComponent from './AddPublicProblem.vue'
import api from '../../api.js'
import utils from '@/utils/utils'
import time from '@/utils/time'
const route = useRoute()
const router = useRouter()

const pageSize = 10
const total = ref(0)
const problemList = ref([])
const keyword = ref('')
const loading = ref(false)
const currentPage = ref(1)
const routeName = ref('')
const contestId = ref('')
const currentRow = ref({})
const inlineEditDialogVisible = ref(false)
const addProblemDialogVisible = ref(false)

function localtime (val) { return time.utcToLocal(val) }

// 스위치를 잠근 이유를 알려준다. 잠긴 채로 두면 관리자가 왜 못 켜는지 알 수 없다.
function lockedReason (row) {
  if (row.visibility === 'pending') {
    return '교사가 공개를 신청했습니다. "문제 공개 신청" 에서 승인하면 켜집니다.'
  }
  return '교사가 만든 비공개 문제입니다. 공개 신청을 승인하면 켜집니다.'
}

function handleDblclick (row) { row.isEditing = true }

function goEdit (problemId) {
  if (routeName.value === 'problem-list') {
    router.push({ name: 'edit-problem', params: { problemId } })
  } else if (routeName.value === 'contest-problem-list') {
    router.push({ name: 'edit-contest-problem', params: { problemId, contestId: contestId.value } })
  }
}

function goCreateProblem () {
  if (routeName.value === 'problem-list') {
    router.push({ name: 'create-problem' })
  } else if (routeName.value === 'contest-problem-list') {
    router.push({ name: 'create-contest-problem', params: { contestId: contestId.value } })
  }
}

function currentChange (page) {
  currentPage.value = page
  getProblemList(page)
}

function getProblemList (page = 1) {
  loading.value = true
  const funcName = routeName.value === 'problem-list' ? 'getProblemList' : 'getContestProblemList'
  const params = { limit: pageSize, offset: (page - 1) * pageSize, keyword: keyword.value, contest_id: contestId.value }
  api[funcName](params).then(res => {
    loading.value = false
    total.value = res.data.data.total
    for (const problem of res.data.data.results) {
      problem.isEditing = false
    }
    problemList.value = res.data.data.results
  }, () => { loading.value = false })
}

function deleteProblem (id) {
  ElMessageBox.confirm('이 문제를 삭제하시겠습니까? 관련 제출 기록도 함께 삭제됩니다.', '문제 삭제', {
    type: 'warning'
  }).then(() => {
    const funcName = routeName.value === 'problem-list' ? 'deleteProblem' : 'deleteContestProblem'
    api[funcName](id).then(() => getProblemList(currentPage.value - 1)).catch(() => {})
  }, () => {})
}

function makeContestProblemPublic (problemID) {
  ElMessageBox.prompt('공개 문제의 표시 ID를 입력하세요', '확인').then(({ value }) => {
    api.makeContestProblemPublic({ id: problemID, display_id: value }).catch(() => {})
  }, () => {})
}

function updateProblem (row) {
  const data = Object.assign({}, row)
  let funcName = ''
  if (contestId.value) {
    data.contest_id = contestId.value
    funcName = 'editContestProblem'
  } else {
    funcName = 'editProblem'
  }
  api[funcName](data).then(() => {
    inlineEditDialogVisible.value = false
    getProblemList(currentPage.value)
  }).catch(() => { inlineEditDialogVisible.value = false })
}

function handleInlineEdit (row) {
  currentRow.value = row
  inlineEditDialogVisible.value = true
}

function downloadTestCase (problemID) {
  utils.downloadFile('/admin/test_case?problem_id=' + problemID)
}

onMounted(() => {
  routeName.value = route.name
  contestId.value = route.params.contestId || ''
  getProblemList(currentPage.value)
})

watch(() => route.fullPath, () => {
  contestId.value = route.params.contestId || ''
  routeName.value = route.name
  getProblemList(currentPage.value)
})

watch(keyword, () => { currentChange(1) })
</script>

<style scoped>
.state-tag {
  margin-left: 6px;
}

.full-width {
  width: 100%;
}
</style>
