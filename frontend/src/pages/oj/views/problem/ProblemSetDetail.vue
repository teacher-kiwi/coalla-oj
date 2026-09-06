<template>
  <Panel shadow>
    <template #title>{{ info.title || '문제집' }}</template>
    <template #extra>
      <el-button @click="goList">목록</el-button>
    </template>

    <Markdown v-if="info.description" class="description panel-inset" :source="info.description" />
    <p class="meta panel-inset">
      <span v-if="info.class_name">{{ info.class_name }}</span>
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
      <el-table-column label="#" prop="display_id" width="100" />
      <el-table-column label="제목">
        <template #default="{ row }">
          <el-button v-if="row.available !== false" link type="primary"
                     @click="goProblem(row.display_id)">{{ row.title }}</el-button>
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
      <template #empty>
        <span v-if="!loading">아직 문제가 담기지 않은 문제집입니다.</span>
      </template>
    </el-table>

    <p v-if="hasUnavailable" class="notice panel-inset">
      "지금 풀 수 없습니다" 로 표시된 문제는 선생님께 문의해주세요.
    </p>
  </Panel>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import Markdown from '@oj/components/Markdown.vue'
import { useRoute, useRouter } from 'vue-router'
import { CircleCheck, CircleClose } from '@element-plus/icons-vue'
import api from '@oj/api'
import DifficultyTag from '@oj/components/DifficultyTag.vue'

const route = useRoute()
const router = useRouter()
const setId = route.params.setId

const loading = ref(false)
const info = ref({ problems: [] })

const solvedCount = computed(() => info.value.problems.filter(p => p.my_status === 0).length)
const hasUnavailable = computed(() => info.value.problems.some(p => p.available === false))

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

/* 교사가 적은 안내. 마크다운으로 그린다(학생 화면과 같은 렌더러).
   색·줄간격·줄바꿈은 마크다운 쪽이 정하므로 여기서는 간격만 잡는다. */
.description {
  margin-bottom: 12px;
}

.meta {
  display: flex;
  gap: 20px;
  font-size: 13px;
  color: #909399;
  margin-bottom: 12px;
}

</style>
