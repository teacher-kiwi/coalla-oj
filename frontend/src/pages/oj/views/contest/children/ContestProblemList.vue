<template>
  <div>
    <Panel>
      <template #title>문제 목록</template>
      <el-table v-if="contestRuleType === 'ACM' || OIContestRealTimePermission"
                :key="statusColumnVisible"
                :data="problems" @row-click="goContestProblem" empty-text="문제 없음">
        <el-table-column label="#" prop="_id" sortable width="150" />
        <el-table-column label="제목" prop="title" />
        <el-table-column label="총 제출" prop="submission_number" />
        <el-table-column label="정답률">
          <template #default="{ row }">{{ getACRate(row.accepted_number, row.submission_number) }}</template>
        </el-table-column>
        <el-table-column v-if="statusColumnVisible" label="상태">
          <template #default="{ row }">
            <template v-if="row.my_status === 0">
              <el-icon color="#19be6b"><CircleCheck /></el-icon>
            </template>
            <template v-else-if="row.my_status !== null && row.my_status !== undefined">
              <el-icon color="#ed3f14"><CircleClose /></el-icon>
            </template>
          </template>
        </el-table-column>
      </el-table>
      <el-table v-else :data="problems" @row-click="goContestProblem" empty-text="문제 없음">
        <el-table-column label="#" prop="_id" width="150" />
        <el-table-column label="제목" prop="title" />
      </el-table>
    </Panel>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { CircleCheck, CircleClose } from '@element-plus/icons-vue'
import utils from '@/utils/utils'
import { useContestStore } from '@/store/contest'
import { useUserStore } from '@/store/user'
const route = useRoute()
const router = useRouter()
const contestStore = useContestStore()
const userStore = useUserStore()

const statusColumnVisible = ref(false)

const problems = computed(() => contestStore.contestProblems)
const contestRuleType = computed(() => contestStore.contestRuleType)
const OIContestRealTimePermission = computed(() => contestStore.OIContestRealTimePermission)

function getACRate (ac, total) {
  return utils.getACRate(ac, total)
}

function goContestProblem (row) {
  router.push({
    name: 'contest-problem-details',
    params: {
      contestID: route.params.contestID,
      problemID: row._id
    }
  })
}

onMounted(() => {
  contestStore.getContestProblems(route.params.contestID).then(res => {
    if (userStore.isAuthenticated && res?.data?.data) {
      statusColumnVisible.value = res.data.data.some(p => p.my_status !== undefined && p.my_status !== null)
    }
  })
})
</script>
