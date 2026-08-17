<template>
  <Panel shadow>
    <template #title>{{ info.title || '문제집' }}</template>
    <template #extra>
      <el-button @click="goList">목록</el-button>
    </template>

    <p v-if="info.description" class="description">{{ info.description }}</p>
    <p class="meta">
      <span v-if="info.class_name">{{ info.class_name }}</span>
      <span v-if="info.due_at" :class="{ overdue: isOverdue }">
        마감 {{ localtime(info.due_at) }}
      </span>
      <span>{{ solvedCount }} / {{ info.problems.length }} 문제 해결</span>
    </p>

    <el-table v-loading="loading" :data="info.problems" class="full-width">
      <el-table-column width="50" align="center">
        <template #default="{ row }">
          <el-icon v-if="row.my_status === 0" color="#19be6b" :size="16"><CircleCheck /></el-icon>
          <el-icon v-else-if="row.my_status !== null && row.my_status !== undefined"
                   color="#ed3f14" :size="16"><CircleClose /></el-icon>
        </template>
      </el-table-column>
      <el-table-column label="#" prop="_id" width="100" />
      <el-table-column label="제목">
        <template #default="{ row }">
          <el-button v-if="row.available !== false" link type="primary"
                     @click="goProblem(row._id)">{{ row.title }}</el-button>
          <template v-else>
            <span class="unavailable">{{ row.title }}</span>
            <!-- 관리자가 문제를 감춘 경우다. 목록에서 조용히 빼면 학생은 이유를 알 수 없다 -->
            <el-tag size="small" type="info" class="unavailable-tag">지금 풀 수 없습니다</el-tag>
          </template>
        </template>
      </el-table-column>
      <el-table-column label="난이도" width="100">
        <template #default="{ row }"><DifficultyTag :value="row.difficulty" /></template>
      </el-table-column>
    </el-table>

    <p v-if="!loading && !info.problems.length" class="empty">
      아직 문제가 담기지 않은 문제집입니다.
    </p>

    <p v-if="hasUnavailable" class="notice">
      "지금 풀 수 없습니다" 로 표시된 문제는 선생님께 문의해주세요.
    </p>
  </Panel>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { CircleCheck, CircleClose } from '@element-plus/icons-vue'
import api from '@oj/api'
import time from '@/utils/time'
import DifficultyTag from '@oj/components/DifficultyTag.vue'

const route = useRoute()
const router = useRouter()
const setId = route.params.setId

const loading = ref(false)
const info = ref({ problems: [] })

const solvedCount = computed(() => info.value.problems.filter(p => p.my_status === 0).length)
const isOverdue = computed(() => !!info.value.due_at && new Date(info.value.due_at) < new Date())
const hasUnavailable = computed(() => info.value.problems.some(p => p.available === false))

function localtime (val) {
  return time.utcToLocal(val)
}

function goList () {
  router.push({ name: 'problem-set-list' })
}

function goProblem (problemID) {
  router.push({ name: 'problem-details', params: { problemID } })
}

onMounted(() => {
  loading.value = true
  api.getAssignedProblemSet(setId).then(res => {
    loading.value = false
    info.value = res.data.data
  }, () => {
    loading.value = false
  })
})
</script>

<style scoped>
.unavailable {
  color: #a8abb2;
}

.unavailable-tag {
  margin-left: 6px;
}

.notice {
  margin-top: 12px;
  font-size: 12px;
  color: #909399;
}

.full-width {
  width: 100%;
}

.description {
  color: #606266;
  line-height: 1.7;
  white-space: pre-wrap;
}

.meta {
  display: flex;
  gap: 20px;
  font-size: 13px;
  color: #909399;
  margin-bottom: 12px;
}

.overdue {
  color: #f56c6c;
}

.empty {
  text-align: center;
  color: #909399;
  padding: 30px 0;
}
</style>
