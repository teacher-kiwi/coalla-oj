<template>
  <div>
    <el-input v-model="keyword" placeholder="검색어" :prefix-icon="SearchIcon" />
    <el-table :data="problems" v-loading="loading">
      <el-table-column label="ID" width="100" prop="id" />
      <el-table-column label="표시 ID" width="200" prop="_id" />
      <el-table-column label="제목" prop="title" />
      <el-table-column label="옵션" align="center" width="100" fixed="right">
        <template #default="{ row }">
          <icon-btn icon="Plus" name="문제 추가" @click="handleAddProblem(row.id)" />
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
  ElMessageBox.prompt('대회 문제의 표시 ID를 입력하세요', '확인').then(({ value }) => {
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
