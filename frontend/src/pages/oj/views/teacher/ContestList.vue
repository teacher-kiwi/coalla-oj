<template>
  <Panel shadow>
    <template #title>대회</template>
    <template #extra>
      <el-button type="primary" :icon="Plus" @click="openDialog()">대회 열기</el-button>
    </template>

    <p class="guide">
      배포한 학급의 학생만 대회에 들어갈 수 있습니다. 진행 중에는 순위가 실시간으로
      바뀌며, 순위 화면을 전체화면으로 띄우면 칠판에 그대로 쓸 수 있습니다.
    </p>

    <el-table v-loading="loading" :data="contests" class="full-width">
      <el-table-column label="제목">
        <template #default="{ row }">
          <el-button link type="primary" @click="goDetail(row.id)">{{ row.title }}</el-button>
          <div v-if="row.description" class="description">{{ row.description }}</div>
        </template>
      </el-table-column>
      <el-table-column label="상태" width="100">
        <template #default="{ row }">
          <el-tag :type="STATUS_TAG[row.status]" size="small">{{ STATUS_LABEL[row.status] }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="기간" width="300">
        <template #default="{ row }">
          {{ localtime(row.start_time) }} ~ {{ localtime(row.end_time) }}
        </template>
      </el-table-column>
      <el-table-column label="문제" prop="problem_count" width="80" />
      <el-table-column label="배포 학급" prop="class_count" width="100" />
      <el-table-column label="관리" width="280">
        <template #default="{ row }">
          <!-- 수정은 상세 화면에서 한다. 목록에는 열어보기와 삭제만 둔다. -->
          <el-button size="small" type="primary" @click="goDetail(row.id)">관리</el-button>
          <el-button size="small" @click="goRank(row.id)">순위</el-button>
          <el-button size="small" type="danger" :disabled="row.status === CONTEST_STATUS.UNDERWAY"
                     @click="remove(row)">삭제</el-button>
        </template>
      </el-table-column>
    </el-table>

    <p v-if="!loading && !contests.length" class="empty">
      아직 연 대회가 없습니다. "대회 열기"로 만든 뒤 문제를 넣고 학급에 배포하세요.
    </p>

    <el-dialog v-model="dialogVisible" title="대회 열기"
               width="520px" :close-on-click-modal="false">
      <el-form label-width="80px">
        <el-form-item label="제목" required>
          <el-input v-model="form.title" maxlength="128" placeholder="예: 2학기 코딩 대회" />
        </el-form-item>
        <el-form-item label="안내">
          <el-input v-model="form.description" type="textarea" :rows="3"
                    placeholder="학생에게 보이는 안내입니다" />
        </el-form-item>
        <el-form-item label="시작" required>
          <el-date-picker v-model="form.start_time" type="datetime" placeholder="시작 시각"
                          format="YYYY-MM-DD HH:mm" />
        </el-form-item>
        <el-form-item label="종료" required>
          <el-date-picker v-model="form.end_time" type="datetime" placeholder="종료 시각"
                          format="YYYY-MM-DD HH:mm" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">취소</el-button>
        <el-button type="primary" :loading="saving" @click="submit">열기</el-button>
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
import { CONTEST_STATUS } from '@/utils/constants'

const STATUS_LABEL = {
  [CONTEST_STATUS.NOT_START]: '시작 전',
  [CONTEST_STATUS.UNDERWAY]: '진행 중',
  [CONTEST_STATUS.ENDED]: '종료'
}
const STATUS_TAG = {
  [CONTEST_STATUS.NOT_START]: 'info',
  [CONTEST_STATUS.UNDERWAY]: 'success',
  [CONTEST_STATUS.ENDED]: ''
}

const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const contests = ref([])
const form = reactive({ title: '', description: '', start_time: '', end_time: '' })

function localtime (val) {
  return time.utcToLocal(val, 'YYYY-M-D HH:mm')
}

function goDetail (id) {
  router.push({ name: 'teacher-contest-detail', params: { contestId: id } })
}

function goRank (id) {
  router.push({ name: 'contest-rank', params: { contestID: id } })
}

function load () {
  loading.value = true
  api.getMyContests().then(res => {
    contests.value = res.data.data
    loading.value = false
  }, () => {
    loading.value = false
  })
}

function openDialog () {
  form.title = ''
  form.description = ''
  form.start_time = ''
  form.end_time = ''
  dialogVisible.value = true
}

function submit () {
  if (!form.title.trim()) {
    ElMessage.error('제목을 입력해주세요')
    return
  }
  if (!form.start_time || !form.end_time) {
    ElMessage.error('시작과 종료 시각을 정해주세요')
    return
  }
  saving.value = true
  const payload = {
    title: form.title,
    description: form.description,
    // toISOString 은 타임존(Z)이 붙는다. 이걸 빼면 서버(TIME_ZONE=UTC)가
    // 교사가 고른 지역 시각을 그대로 UTC 로 읽어 그만큼 어긋난다.
    start_time: new Date(form.start_time).toISOString(),
    end_time: new Date(form.end_time).toISOString()
  }
  api.createMyContest(payload).then(() => {
    saving.value = false
    dialogVisible.value = false
    load()
  }, () => {
    saving.value = false
  })
}

function remove (row) {
  ElMessageBox.confirm(
    `"${row.title}" 대회를 삭제합니다. 대회 문제와 학생들의 제출 기록, 순위가 함께 사라지며 되돌릴 수 없습니다.`,
    '대회 삭제', { confirmButtonText: '삭제', cancelButtonText: '취소', type: 'warning' }
  ).then(() => {
    api.deleteMyContest(row.id).then(load, () => {})
  }).catch(() => {})
}

onMounted(load)
</script>

<style scoped>
.guide {
  font-size: 13px;
  color: #606266;
  line-height: 1.7;
  margin-bottom: 14px;
}

.description {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.empty {
  text-align: center;
  color: #909399;
  padding: 30px 0;
}
</style>
