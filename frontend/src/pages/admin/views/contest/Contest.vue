<template>
  <div class="view">
    <Panel :title="title">
      <el-form label-position="top">
        <el-row :gutter="20">
          <el-col :span="24">
            <el-form-item :label="t('m.ContestTitle')" required>
              <el-input v-model="contest.title" :placeholder="t('m.ContestTitle')" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item :label="t('m.ContestDescription')" required>
              <Simditor v-model="contest.description" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="t('m.Contest_Start_Time')" required>
              <el-date-picker v-model="contest.start_time" type="datetime" :placeholder="t('m.Contest_Start_Time')" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="t('m.Contest_End_Time')" required>
              <el-date-picker v-model="contest.end_time" type="datetime" :placeholder="t('m.Contest_End_Time')" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="t('m.Contest_Password')">
              <el-input v-model="contest.password" :placeholder="t('m.Contest_Password')" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="t('m.Contest_Rule_Type')">
              <el-radio-group v-model="contest.rule_type" :disabled="disableRuleType">
                <el-radio label="ACM">ACM</el-radio>
                <el-radio label="OI">OI</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="t('m.Real_Time_Rank')">
              <el-switch v-model="contest.real_time_rank" active-color="#13ce66" inactive-color="#ff4949" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="t('m.Contest_Status')">
              <el-switch v-model="contest.visible" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item :label="t('m.Allowed_IP_Ranges')">
              <div v-for="(range, index) in contest.allowed_ip_ranges" :key="index">
                <el-row :gutter="20" class="ip-range-row">
                  <el-col :span="8">
                    <el-input v-model="range.value" :placeholder="t('m.CIDR_Network')" />
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
import { useI18n } from 'vue-i18n'
import { Plus, Delete } from '@element-plus/icons-vue'
import Simditor from '../../components/Simditor.vue'
import api from '../../api.js'

const { t } = useI18n()
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
    title.value = 'Edit Contest'
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
