<template>
  <div>
    <Panel shadow>
      <template #title>바로 과제 레포트</template>
      <template #extra>
        <el-button type="primary" :icon="Plus" @click="router.push({ name: 'teacher-homework-create' })">
          만들기
        </el-button>
      </template>

      <el-table v-loading="loading" :data="homeworks" class="full-width" @row-click="open">
        <el-table-column label="상태" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.ended" type="info" effect="plain">종료</el-tag>
            <el-tag v-else type="success">진행 중</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="제목" min-width="200">
          <template #default="{ row }"><span class="link-text">{{ row.title }}</span></template>
        </el-table-column>
        <el-table-column label="코드" prop="code" width="90" />
        <el-table-column label="만든 시각" min-width="120">
          <template #default="{ row }">{{ localtime(row.create_time) }}</template>
        </el-table-column>
        <el-table-column label="마감·종료" min-width="120">
          <template #default="{ row }">{{ localtime(row.ended_at || row.end_time) }}</template>
        </el-table-column>
        <el-table-column label="참가" width="80" align="center">
          <template #default="{ row }">{{ row.participant_count }}명</template>
        </el-table-column>
        <el-table-column label="문제" width="80" align="center">
          <template #default="{ row }">{{ row.problem_count }}개</template>
        </el-table-column>
        <template #empty>
          <span v-if="!loading">만든 바로 과제가 없습니다. "만들기"로 시작하세요.</span>
        </template>
      </el-table>
    </Panel>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Plus } from '@element-plus/icons-vue'
import api from '@oj/api'
import time from '@/utils/time'

const router = useRouter()
const loading = ref(true)
const homeworks = ref([])

function localtime (value) {
  return time.utcToLocal(value, 'YYYY-MM-DD HH:mm')
}

function open (row) {
  router.push({ name: 'teacher-homework-board', params: { id: row.id } })
}

onMounted(() => {
  api.getTeacherHomeworks().then(res => { homeworks.value = res.data.data }, () => {})
    .finally(() => { loading.value = false })
})
</script>

<style lang="less" scoped>
:deep(.el-table__row) {
  cursor: pointer;
}
</style>
