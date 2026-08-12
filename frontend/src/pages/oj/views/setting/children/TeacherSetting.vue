<template>
  <div class="setting-main">
    <p class="section-title">교사 인증</p>
    <div class="mini-container setting-content">
      <el-alert v-if="isTeacher" type="success" show-icon :closable="false" class="notice">
        교사로 승인된 계정입니다. 학급과 문제집을 관리할 수 있습니다.
      </el-alert>

      <template v-else-if="status === 'pending'">
        <el-alert type="info" show-icon :closable="false" class="notice">
          교사 신청이 접수되었습니다. 관리자 승인 후 이용할 수 있습니다.
        </el-alert>
        <p class="guide">신청 일시: {{ localtime(application.applied_at) }}</p>
      </template>

      <template v-else-if="status === 'rejected'">
        <el-alert type="error" show-icon :closable="false" class="notice">
          교사 신청이 반려되었습니다.
        </el-alert>
        <p v-if="application.note" class="guide">사유: {{ application.note }}</p>
        <p class="guide">문의가 필요하시면 관리자에게 연락해주세요.</p>
      </template>

      <template v-else>
        <p class="guide">
          선생님이신가요? 교사로 승인받으면 학급을 만들고, 학생 계정을 발급하고,
          문제집을 만들어 학생들에게 내줄 수 있습니다.
        </p>
        <p class="guide">신청 후 관리자 확인을 거쳐 승인됩니다.</p>
        <el-button type="primary" :loading="loading" @click="apply">교사 신청하기</el-button>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@oj/api'
import time from '@/utils/time'
import { useUserStore } from '@/store/user'

const userStore = useUserStore()
const application = ref(null)
const loading = ref(false)

const isTeacher = computed(() => userStore.isTeacher)
const status = computed(() => application.value?.status || null)

function localtime (val) {
  return val ? time.utcToLocal(val) : '-'
}

function load () {
  api.getMyTeacherApplication().then(res => {
    application.value = res.data.data
  }, () => {})
}

function apply () {
  loading.value = true
  api.applyForTeacher().then(res => {
    loading.value = false
    application.value = res.data.data
    ElMessage.success('교사 신청이 접수되었습니다')
  }, () => {
    loading.value = false
  })
}

onMounted(load)
</script>

<style scoped>
.notice {
  margin-bottom: 16px;
}

.guide {
  font-size: 14px;
  color: #606266;
  line-height: 1.7;
  margin-bottom: 12px;
}
</style>
