<template>
  <div class="view">
    <Panel :title="contestId ? '대회 문제 목록' : '문제 목록'">
      <template #header>
        <el-input v-model="keyword" :prefix-icon="SearchIcon" placeholder="검색어" />
      </template>
      <el-table v-loading="loading" :data="problemList" @row-dblclick="handleDblclick" class="full-width">
        <!-- 공개 문제는 번호가 곧 pk 이고, 대회 문제는 담은 순서가 정한다.
             어느 쪽도 사람이 고치지 않는다. -->
        <el-table-column width="120" prop="display_id" label="번호" />
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
            <icon-btn icon="Download" name="테스트 케이스 내려받기" @click="downloadTestCase(row.id)" />
            <!-- 대회 화면에서는 문제를 지우지 않고 대회에서 빼기만 한다.
                 문제는 대회 밖에서도 쓰이고, 지우면 제출 기록이 함께 사라진다. -->
            <icon-btn v-if="contestId" icon="Remove" name="대회에서 빼기"
                      @click="removeFromContest(row.id)" />
            <icon-btn v-else icon="Delete" name="문제 삭제" @click="deleteProblem(row.id)" />
          </template>
        </el-table-column>
      </el-table>
      <div class="panel-options">
        <el-button v-if="!contestId" type="primary" size="small"
                   @click="goCreateProblem" :icon="Plus">생성</el-button>
        <el-button v-else type="primary" size="small" :icon="Plus"
                   @click="addProblemDialogVisible = true">문제 담기</el-button>
        <el-pagination class="page" layout="prev, pager, next"
                       @current-change="currentChange" :page-size="pageSize" :total="total" />
      </div>
    </Panel>

    <el-dialog title="문제를 수정하시겠습니까?" width="20%" v-model="inlineEditDialogVisible"
               :close-on-click-modal="false">
      <div>
        <p>번호: {{ currentRow.display_id }}</p>
        <p>제목: {{ currentRow.title }}</p>
      </div>
      <template #footer>
        <cancel @click="inlineEditDialogVisible = false; getProblemList(currentPage)" />
        <save @click="updateProblem(currentRow)" />
      </template>
    </el-dialog>

    <el-dialog v-if="contestId" title="대회에 문제 담기" width="80%" v-model="addProblemDialogVisible"
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

// 대회 문제도 그냥 문제다. 어느 화면에서 왔든 같은 수정 화면으로 간다.
function goEdit (problemId) {
  router.push({ name: 'edit-problem', params: { problemId } })
}

function goCreateProblem () {
  router.push({ name: 'create-problem' })
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
    api.deleteProblem(id).then(() => getProblemList(currentPage.value - 1)).catch(() => {})
  }, () => {})
}

function removeFromContest (problemId) {
  ElMessageBox.confirm('이 문제를 대회에서 빼시겠습니까? 문제 자체는 남습니다.', '대회에서 빼기')
    .then(() => {
      api.removeProblemFromContest(contestId.value, problemId)
        .then(() => getProblemList(currentPage.value)).catch(() => {})
    }, () => {})
}

function updateProblem (row) {
  const data = Object.assign({}, row)
  api.editProblem(data).then(() => {
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
