<template>
  <div class="view">
    <Panel title="교사 가입 신청">
      <template #header>
        <el-radio-group v-model="status" @change="changeStatus">
          <el-radio-button value="pending">승인 대기</el-radio-button>
          <el-radio-button value="approved">승인됨</el-radio-button>
          <el-radio-button value="rejected">반려됨</el-radio-button>
          <el-radio-button value="">전체</el-radio-button>
        </el-radio-group>
      </template>

      <el-table v-loading="loading" :data="applications" class="full-width">
        <el-table-column prop="username" label="사용자명" width="160" />
        <el-table-column prop="real_name" label="이름" width="120" />
        <el-table-column prop="email" label="이메일" />
        <el-table-column prop="applied_at" label="신청 일시" width="180">
          <template #default="{ row }">{{ localtime(row.applied_at) }}</template>
        </el-table-column>
        <el-table-column label="상태" width="110">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="note" label="비고" />
        <el-table-column fixed="right" label="처리" width="160">
          <template #default="{ row }">
            <template v-if="row.status === 'pending'">
              <el-button type="success" size="small" @click="review(row, 'approved')">승인</el-button>
              <el-button type="danger" size="small" @click="review(row, 'rejected')">반려</el-button>
            </template>
            <span v-else class="reviewed">{{ row.reviewed_by || '-' }}</span>
          </template>
        </el-table-column>
      </el-table>

      <div class="panel-options">
        <el-pagination class="page" layout="prev, pager, next" :current-page="currentPage"
                       @current-change="currentChange" :page-size="pageSize" :total="total" />
      </div>
    </Panel>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessageBox } from 'element-plus'
import api from '../../api.js'
import time from '@/utils/time'

const pageSize = 15
const total = ref(0)
const currentPage = ref(1)
const status = ref('pending')
const loading = ref(false)
const applications = ref([])

function localtime (val) {
  return val ? time.utcToLocal(val) : '-'
}

function statusLabel (s) {
  return { pending: '대기', approved: '승인', rejected: '반려' }[s] || s
}

function statusType (s) {
  return { pending: 'warning', approved: 'success', rejected: 'danger' }[s] || 'info'
}

function getApplications (page = 1) {
  loading.value = true
  api.getTeacherApplicationList((page - 1) * pageSize, pageSize, status.value).then(res => {
    loading.value = false
    total.value = res.data.data.total
    applications.value = res.data.data.results
  }, () => {
    loading.value = false
  })
}

function currentChange (page) {
  currentPage.value = page
  getApplications(page)
}

function changeStatus () {
  currentChange(1)
}

function review (row, next) {
  const isApprove = next === 'approved'
  const message = isApprove
    ? `${row.username} 님을 교사로 승인하시겠습니까?`
    : `${row.username} 님의 신청을 반려하시겠습니까?`
  ElMessageBox.confirm(message, isApprove ? '교사 승인' : '신청 반려', {
    confirmButtonText: isApprove ? '승인' : '반려',
    cancelButtonText: '취소',
    type: isApprove ? 'success' : 'warning'
  }).then(() => {
    api.reviewTeacherApplication({ id: row.id, status: next })
      .then(() => getApplications(currentPage.value))
      .catch(() => {})
  }).catch(() => {})
}

onMounted(() => getApplications())
</script>

<style scoped>
.full-width {
  width: 100%;
}

.reviewed {
  color: #909399;
  font-size: 13px;
}
</style>
