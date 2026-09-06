<template>
  <Panel shadow>
    <template #title>내 문제집</template>

    <el-table v-loading="loading" :data="problemSets" class="full-width">
      <el-table-column label="문제집">
        <template #default="{ row }">
          <el-button link type="primary" @click="goDetail(row.id)">{{ row.title }}</el-button>
          <div v-if="row.description" class="description">{{ row.description }}</div>
        </template>
      </el-table-column>
      <el-table-column label="학급" prop="class_name" width="260" />
      <el-table-column label="진행" width="200">
        <template #default="{ row }">
          <el-progress :percentage="percentage(row)" :stroke-width="14"
                       :format="() => `${row.solved_count} / ${row.problem_count}`" />
        </template>
      </el-table-column>
      <template #empty>
        <span v-if="!loading">선생님이 배포한 문제집이 없습니다.</span>
      </template>
    </el-table>
  </Panel>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@oj/api'

const router = useRouter()
const loading = ref(false)
const problemSets = ref([])

function percentage (row) {
  if (!row.problem_count) return 0
  return Math.round((row.solved_count / row.problem_count) * 100)
}

function goDetail (id) {
  router.push({ name: 'problem-set-detail', params: { setId: id } })
}

onMounted(() => {
  loading.value = true
  api.getMyAssignedProblemSets().then(res => {
    loading.value = false
    problemSets.value = res.data.data
  }, () => {
    loading.value = false
  })
})
</script>

<style scoped>
.full-width {
  width: 100%;
}

.description {
  font-size: 12px;
  color: #909399;
  line-height: 1.6;
}

</style>
