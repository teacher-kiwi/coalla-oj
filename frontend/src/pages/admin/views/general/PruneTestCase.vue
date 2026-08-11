<template>
  <div>
    <Panel>
      <template #title>
        테스트 케이스 정리
        <el-popover placement="right" trigger="hover">
          <template #reference><el-icon class="help-icon"><QuestionFilled /></el-icon></template>
          These test cases are not owned by any problem, you can clean them safely.
        </el-popover>
      </template>
      <el-table :data="data">
        <el-table-column label="최종 수정">
          <template #default="{ row }">{{ timestampFormat(row.create_time) }}</template>
        </el-table-column>
        <el-table-column prop="id" label="테스트 케이스 ID" />
        <el-table-column label="옵션" fixed="right" width="200">
          <template #default="{ row }">
            <icon-btn name="삭제" icon="Delete" @click="deleteTestCase(row.id)" />
          </template>
        </el-table-column>
      </el-table>
      <div class="panel-options" v-show="data.length > 0">
        <el-button type="warning" size="small" :loading="loading" @click="deleteTestCase()">전체 삭제</el-button>
      </div>
    </Panel>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { QuestionFilled } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import api from '@admin/api'

const data = ref([])
const loading = ref(false)

function timestampFormat (value) {
  return dayjs.unix(value).format('YYYY-M-D  HH:mm:ss')
}

function init () {
  api.getInvalidTestCaseList().then(resp => {
    data.value = resp.data.data
  }, () => {})
}

function deleteTestCase (id) {
  if (!id) loading.value = true
  api.pruneTestCase(id).then(() => {
    loading.value = false
    init()
  })
}

onMounted(() => { init() })
</script>

<style scoped>
.help-icon {
  margin-left: 4px;
}
</style>
