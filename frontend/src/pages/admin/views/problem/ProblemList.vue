<template>
  <div class="view">
    <Panel :title="contestId ? t('m.Contest_Problem_List') : t('m.Problem_List')">
      <template #header>
        <el-input v-model="keyword" :prefix-icon="SearchIcon" placeholder="Keywords" />
      </template>
      <el-table v-loading="loading" :data="problemList" @row-dblclick="handleDblclick" class="full-width">
        <el-table-column width="100" prop="id" label="ID" />
        <el-table-column width="150" label="Display ID">
          <template #default="{ row }">
            <span v-show="!row.isEditing">{{ row._id }}</span>
            <el-input v-show="row.isEditing" v-model="row._id" @keyup.enter="handleInlineEdit(row)" />
          </template>
        </el-table-column>
        <el-table-column prop="title" label="Title">
          <template #default="{ row }">
            <span v-show="!row.isEditing">{{ row.title }}</span>
            <el-input v-show="row.isEditing" v-model="row.title" @keyup.enter="handleInlineEdit(row)" />
          </template>
        </el-table-column>
        <el-table-column prop="created_by.username" label="Author" />
        <el-table-column width="200" prop="create_time" label="Create Time">
          <template #default="{ row }">{{ localtime(row.create_time) }}</template>
        </el-table-column>
        <el-table-column width="100" prop="visible" label="Visible">
          <template #default="{ row }">
            <el-switch v-model="row.visible" @change="updateProblem(row)" />
          </template>
        </el-table-column>
        <el-table-column fixed="right" label="Operation" width="250">
          <template #default="{ row }">
            <icon-btn name="Edit" icon="Edit" @click="goEdit(row.id)" />
            <icon-btn v-if="contestId" name="Make Public" icon="CopyDocument" @click="makeContestProblemPublic(row.id)" />
            <icon-btn icon="Download" name="Download TestCase" @click="downloadTestCase(row.id)" />
            <icon-btn icon="Delete" name="Delete Problem" @click="deleteProblem(row.id)" />
          </template>
        </el-table-column>
      </el-table>
      <div class="panel-options">
        <el-button type="primary" size="small" @click="goCreateProblem" :icon="Plus">Create</el-button>
        <el-button v-if="contestId" type="primary" size="small" :icon="Plus"
                   @click="addProblemDialogVisible = true">Add From Public Problem</el-button>
        <el-pagination class="page" layout="prev, pager, next"
                       @current-change="currentChange" :page-size="pageSize" :total="total" />
      </div>
    </Panel>

    <el-dialog title="Sure to update the problem?" width="20%" v-model="inlineEditDialogVisible"
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

    <el-dialog v-if="contestId" title="Add Contest Problem" width="80%" v-model="addProblemDialogVisible"
               :close-on-click-modal="false">
      <AddProblemComponent :contestID="contestId" @on-change="getProblemList" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessageBox } from 'element-plus'
import { Plus, Search as SearchIcon } from '@element-plus/icons-vue'
import AddProblemComponent from './AddPublicProblem.vue'
import api from '../../api.js'
import utils from '@/utils/utils'
import time from '@/utils/time'

const { t } = useI18n()
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
  ElMessageBox.confirm('Sure to delete this problem? The associated submissions will be deleted as well.', 'Delete Problem', {
    type: 'warning'
  }).then(() => {
    const funcName = routeName.value === 'problem-list' ? 'deleteProblem' : 'deleteContestProblem'
    api[funcName](id).then(() => getProblemList(currentPage.value - 1)).catch(() => {})
  }, () => {})
}

function makeContestProblemPublic (problemID) {
  ElMessageBox.prompt('Please input display id for the public problem', 'Confirm').then(({ value }) => {
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
.full-width {
  width: 100%;
}
</style>
