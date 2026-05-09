<template>
  <div>
    <el-input v-model="keyword" placeholder="Keywords" :prefix-icon="SearchIcon" />
    <el-table :data="problems" v-loading="loading">
      <el-table-column label="ID" width="100" prop="id" />
      <el-table-column label="DisplayID" width="200" prop="_id" />
      <el-table-column label="Title" prop="title" />
      <el-table-column label="Option" align="center" width="100" fixed="right">
        <template #default="{ row }">
          <icon-btn icon="Plus" name="Add the problem" @click="handleAddProblem(row.id)" />
        </template>
      </el-table-column>
    </el-table>
    <el-pagination class="page" layout="prev, pager, next"
                   @current-change="getPublicProblem" :page-size="limit" :total="total" />
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { Search as SearchIcon } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import api from '@admin/api'

const props = defineProps({ contestID: { type: [String, Number], required: true } })
const emit = defineEmits(['on-change'])

const limit = 10
const total = ref(0)
const loading = ref(false)
const problems = ref([])
const contest = ref({})
const keyword = ref('')

onMounted(() => {
  api.getContest(props.contestID).then(res => {
    contest.value = res.data.data
    getPublicProblem()
  }).catch(() => {})
})

function getPublicProblem (page = 1) {
  loading.value = true
  api.getProblemList({
    keyword: keyword.value,
    offset: (page - 1) * limit,
    limit,
    rule_type: contest.value.rule_type
  }).then(res => {
    loading.value = false
    total.value = res.data.data.total
    problems.value = res.data.data.results
  }).catch(() => { loading.value = false })
}

function handleAddProblem (problemID) {
  ElMessageBox.prompt('Please input display id for the contest problem', 'Confirm').then(({ value }) => {
    api.addProblemFromPublic({ problem_id: problemID, contest_id: props.contestID, display_id: value }).then(() => {
      emit('on-change')
    }, () => {})
  }, () => {})
}

watch(keyword, () => { getPublicProblem(1) })
</script>

<style scoped>
.page { margin-top: 20px; text-align: right; }
</style>
