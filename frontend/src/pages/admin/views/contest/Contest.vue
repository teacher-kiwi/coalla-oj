<template>
  <div class="view">
    <Panel :title="title">
      <el-form label-position="top">
        <el-row :gutter="20">
          <el-col :span="24">
            <el-form-item label="제목" required>
              <el-input v-model="contest.title" placeholder="제목" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="설명" required>
              <Simditor v-model="contest.description" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="시작 시간" required>
              <el-date-picker v-model="contest.start_time" type="datetime" placeholder="시작 시간" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="종료 시간" required>
              <el-date-picker v-model="contest.end_time" type="datetime" placeholder="종료 시간" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="비밀번호">
              <el-input v-model="contest.password" placeholder="비밀번호" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="대회 규칙 유형">
              <el-radio-group v-model="contest.rule_type" :disabled="disableRuleType">
                <el-radio label="ACM">ACM</el-radio>
                <el-radio label="OI">OI</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="실시간 순위">
              <el-switch v-model="contest.real_time_rank" active-color="#13ce66" inactive-color="#ff4949" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="상태">
              <el-switch v-model="contest.visible" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="허용된 IP 범위">
              <div v-for="(range, index) in contest.allowed_ip_ranges" :key="index">
                <el-row :gutter="20" class="ip-range-row">
                  <el-col :span="8">
                    <el-input v-model="range.value" placeholder="CIDR 네트워크" />
                  </el-col>
                  <el-col :span="10">
                    <el-button plain :icon="Plus" @click="addIPRange" />
                    <el-button plain :icon="Delete" @click="removeIPRange(range)" />
                  </el-col>
                </el-row>
              </div>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <save @click="saveContest" />
    </Panel>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Plus, Delete } from '@element-plus/icons-vue'
import Simditor from '../../components/Simditor.vue'
import api from '../../api.js'
const route = useRoute()
const router = useRouter()

const title = ref('Create Contest')
const disableRuleType = ref(false)
const contest = reactive({
  title: '',
  description: '',
  start_time: '',
  end_time: '',
  rule_type: 'ACM',
  password: '',
  real_time_rank: true,
  visible: true,
  allowed_ip_ranges: [{ value: '' }]
})

function saveContest () {
  const funcName = route.name === 'edit-contest' ? 'editContest' : 'createContest'
  const data = Object.assign({}, contest)
  data.allowed_ip_ranges = data.allowed_ip_ranges.filter(v => v.value !== '').map(v => v.value)
  api[funcName](data).then(() => {
    router.push({ name: 'contest-list', query: { refresh: 'true' } })
  }).catch(() => {})
}

function addIPRange () { contest.allowed_ip_ranges.push({ value: '' }) }

function removeIPRange (range) {
  const index = contest.allowed_ip_ranges.indexOf(range)
  if (index !== -1) contest.allowed_ip_ranges.splice(index, 1)
}

onMounted(() => {
  if (route.name === 'edit-contest') {
    title.value = '대회 수정'
    disableRuleType.value = true
    api.getContest(route.params.contestId).then(res => {
      const data = res.data.data
      const ranges = data.allowed_ip_ranges.map(v => ({ value: v }))
      if (ranges.length === 0) ranges.push({ value: '' })
      data.allowed_ip_ranges = ranges
      Object.assign(contest, data)
    }).catch(() => {})
  }
})
</script>

<style scoped>
.ip-range-row {
  margin-bottom: 15px;
}
</style>
