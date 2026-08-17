<template>
  <Panel shadow>
    <template #title>내가 만든 문제</template>
    <template #extra>
      <el-button type="primary" :icon="Plus" @click="goCreate">문제 만들기</el-button>
    </template>

    <el-table v-loading="loading" :data="problems" class="full-width">
      <el-table-column label="번호" prop="_id" width="90" />
      <el-table-column label="제목">
        <template #default="{ row }">
          <el-button link type="primary" @click="goProblem(row._id)">{{ row.title }}</el-button>
        </template>
      </el-table-column>
      <el-table-column label="난이도" width="100" align="center">
        <template #default="{ row }"><DifficultyTag :value="row.difficulty" /></template>
      </el-table-column>
      <el-table-column label="태그" width="180">
        <template #default="{ row }">
          <el-tag v-for="tag in row.tags" :key="tag" size="small" class="tag-item">{{ tag }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="공개" width="110" align="center">
        <template #default="{ row }">
          <el-tag :type="STATE[row.visibility].type" size="small">
            {{ STATE[row.visibility].label }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="제출" width="80" align="center" prop="submission_number" />
      <el-table-column label="관리" width="300">
        <template #default="{ row }">
          <el-button size="small" :disabled="row.visibility === 'public'"
                     @click="goEdit(row.id)">수정</el-button>
          <el-button v-if="row.visibility === 'private'" size="small" type="success"
                     @click="requestPublish(row)">공개 신청</el-button>
          <el-button v-else-if="row.visibility === 'pending'" size="small"
                     @click="cancelPublish(row)">신청 취소</el-button>
          <el-button size="small" type="danger" :disabled="row.visibility === 'public'"
                     @click="remove(row)">삭제</el-button>
        </template>
      </el-table-column>
    </el-table>

    <p v-if="!loading && !problems.length" class="empty">
      아직 만든 문제가 없습니다. "문제 만들기"로 시작하세요.<br />
      만든 문제는 비공개로 저장되고, 문제집에 담아 학급에 배포하면 학생이 풀 수 있습니다.
    </p>

    <p v-if="problems.length" class="guide">
      비공개 문제는 나와 내가 배포한 학급 학생만 볼 수 있습니다.
      다른 선생님도 쓸 수 있게 하려면 공개를 신청하세요. 관리자 승인 후 공개됩니다.
    </p>
  </Panel>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '@oj/api'
import DifficultyTag from '@oj/components/DifficultyTag.vue'

const router = useRouter()
const loading = ref(false)
const problems = ref([])

const STATE = {
  private: { label: '비공개', type: 'info' },
  pending: { label: '승인 대기', type: 'warning' },
  public: { label: '공개', type: 'success' }
}

function load () {
  loading.value = true
  api.getMyProblems().then(res => {
    loading.value = false
    problems.value = res.data.data
  }, () => {
    loading.value = false
  })
}

function goCreate () {
  router.push({ name: 'teacher-problem-create' })
}

function goEdit (id) {
  router.push({ name: 'teacher-problem-edit', params: { problemId: id } })
}

function goProblem (problemID) {
  router.push({ name: 'problem-details', params: { problemID } })
}

function requestPublish (row) {
  ElMessageBox.confirm(
    `"${row.title}" 을(를) 공개 신청합니다. 관리자가 승인하면 모든 사용자가 풀 수 있고, ` +
    '그 뒤에는 직접 수정하거나 삭제할 수 없습니다.',
    '공개 신청', { confirmButtonText: '신청', cancelButtonText: '취소' }
  ).then(() => {
    api.requestProblemPublish(row.id).then(() => {
      ElMessage.success('공개를 신청했습니다')
      load()
    }).catch(() => {})
  }).catch(() => {})
}

function cancelPublish (row) {
  api.cancelProblemPublish(row.id).then(() => {
    ElMessage.success('신청을 취소했습니다')
    load()
  }).catch(() => {})
}

function remove (row) {
  ElMessageBox.confirm(`"${row.title}" 문제를 삭제합니다.`, '문제 삭제',
                       { confirmButtonText: '삭제', cancelButtonText: '취소', type: 'warning' })
    .then(() => {
      api.deleteProblem(row.id).then(() => {
        ElMessage.success('삭제했습니다')
        load()
      }).catch(() => {})
    }).catch(() => {})
}

onMounted(load)
</script>

<style scoped>
.full-width {
  width: 100%;
}

.tag-item {
  margin-right: 4px;
}

.empty {
  text-align: center;
  color: #909399;
  padding: 30px 0;
  line-height: 1.8;
}

.guide {
  margin-top: 14px;
  font-size: 12px;
  color: #909399;
  line-height: 1.7;
}
</style>
