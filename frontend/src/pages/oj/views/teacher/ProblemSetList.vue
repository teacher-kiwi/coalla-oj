<template>
  <Panel shadow>
    <template #title>문제집</template>
    <template #extra>
      <el-button type="primary" :icon="Plus" @click="openDialog()">문제집 만들기</el-button>
    </template>

    <el-table v-loading="loading" :data="problemSets" class="full-width">
      <el-table-column label="제목">
        <template #default="{ row }">
          <el-button link type="primary" @click="goDetail(row.id)">{{ row.title }}</el-button>
          <div v-if="row.description" class="description">{{ row.description }}</div>
        </template>
      </el-table-column>
      <el-table-column label="문제 수" prop="problem_count" width="100" />
      <el-table-column label="배포 학급" prop="assignment_count" width="100" />
      <el-table-column label="수정" width="180">
        <template #default="{ row }">{{ localtime(row.last_update_time) }}</template>
      </el-table-column>
      <el-table-column label="관리" width="260">
        <template #default="{ row }">
          <el-button size="small" type="primary" @click="goDetail(row.id)">문제·배포 관리</el-button>
          <el-button size="small" @click="openDialog(row)">이름 변경</el-button>
          <el-button size="small" type="danger" @click="remove(row)">삭제</el-button>
        </template>
      </el-table-column>
    </el-table>

    <p v-if="!loading && !problemSets.length" class="empty">
      아직 만든 문제집이 없습니다. "문제집 만들기"로 시작한 뒤 문제를 담고 학급에 배포하세요.
    </p>

    <el-dialog v-model="dialogVisible" :title="form.id ? '문제집 이름 변경' : '문제집 만들기'"
               width="460px" :close-on-click-modal="false">
      <el-form label-width="80px">
        <el-form-item label="제목" required>
          <el-input v-model="form.title" maxlength="128" placeholder="예: 3주차 반복문" />
        </el-form-item>
        <el-form-item label="설명">
          <el-input v-model="form.description" type="textarea" :rows="3" maxlength="1024"
                    placeholder="학생에게 보이는 안내입니다" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">취소</el-button>
        <el-button type="primary" :loading="saving" @click="submit">
          {{ form.id ? '저장' : '만들기' }}
        </el-button>
      </template>
    </el-dialog>
  </Panel>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '@oj/api'
import time from '@/utils/time'

const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const problemSets = ref([])
const form = reactive({ id: null, title: '', description: '' })

function localtime (val) {
  return time.utcToLocal(val)
}

function load () {
  loading.value = true
  api.getMyProblemSets().then(res => {
    loading.value = false
    problemSets.value = res.data.data
  }, () => {
    loading.value = false
  })
}

function openDialog (row) {
  form.id = row ? row.id : null
  form.title = row ? row.title : ''
  form.description = row ? row.description : ''
  dialogVisible.value = true
}

function submit () {
  if (!form.title.trim()) {
    ElMessage.error('제목을 입력하세요')
    return
  }
  const data = { title: form.title.trim(), description: form.description }
  saving.value = true
  const request = form.id
    ? api.editProblemSet({ ...data, id: form.id })
    : api.createProblemSet(data)
  request.then(() => {
    saving.value = false
    dialogVisible.value = false
    load()
  }, () => {
    saving.value = false
  })
}

function remove (row) {
  ElMessageBox.confirm(
    `"${row.title}" 문제집을 삭제합니다. 배포한 학급에서도 사라집니다.\n` +
    '학생이 푼 기록은 문제에 남아 있어 사라지지 않습니다.',
    '문제집 삭제', { confirmButtonText: '삭제', cancelButtonText: '취소', type: 'warning' }
  ).then(() => {
    api.deleteProblemSet(row.id).then(() => {
      ElMessage.success('삭제했습니다')
      load()
    }).catch(() => {})
  }).catch(() => {})
}

function goDetail (id) {
  router.push({ name: 'teacher-problem-set-detail', params: { setId: id } })
}

onMounted(load)
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

.empty {
  text-align: center;
  color: #909399;
  padding: 30px 0;
}
</style>
