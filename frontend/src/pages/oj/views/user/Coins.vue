<template>
  <div class="coins">
    <Panel shadow>
      <template #title>내 코인</template>
      <div class="summary panel-inset">
        <div class="balance">
          <span class="num">{{ balance }}</span>
          <span class="unit">코인</span>
        </div>
        <ul class="ways">
          <li>연습 문제를 <b>처음 맞히면 +10</b></li>
          <li>하루 <b>첫 접속(출석) +5</b></li>
          <li>모은 코인은 곧 열리는 샵에서 캐릭터 꾸미기에 써요</li>
        </ul>
      </div>
      <el-table v-loading="loading" :data="logs" empty-text="아직 받은 코인이 없습니다">
        <el-table-column label="날짜" width="170">
          <template #default="{ row }">{{ time.utcToLocal(row.create_time) }}</template>
        </el-table-column>
        <el-table-column label="내용" min-width="240">
          <template #default="{ row }">
            <template v-if="row.reason === 'solve'">
              문제 정답 ·
              <a class="link-text" @click="goProblem(row.ref)">{{ row.title || `${row.ref}번 문제` }}</a>
            </template>
            <template v-else-if="row.reason === 'attend'">출석</template>
            <template v-else-if="row.reason === 'buy'">아이템 구매</template>
            <template v-else>{{ row.reason }}</template>
          </template>
        </el-table-column>
        <el-table-column label="코인" width="110" align="right">
          <template #default="{ row }">
            <span :class="row.amount >= 0 ? 'plus' : 'minus'">{{ row.amount >= 0 ? '+' : '' }}{{ row.amount }}</span>
          </template>
        </el-table-column>
      </el-table>
      <Pagination :total="total" :page-size="limit" :current="page" @on-change="load" />
    </Panel>
  </div>
</template>

<script setup>
// 내 코인 잔액과 받은·쓴 내역. 코인은 원장(CoinLog)의 합이라 내역을 다 더하면 잔액이 된다.
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@oj/api'
import Panel from '@oj/components/Panel.vue'
import Pagination from '@oj/components/Pagination.vue'
import time from '@/utils/time'
import { useUserStore } from '@/store/user'

const router = useRouter()
const userStore = useUserStore()
const limit = 20
const page = ref(1)
const total = ref(0)
const logs = ref([])
const balance = ref(userStore.coins)
const loading = ref(false)

function load (p = 1) {
  page.value = p
  loading.value = true
  api.getCoinLog((p - 1) * limit, limit).then(res => {
    const data = res.data.data
    logs.value = data.results
    total.value = data.total
    balance.value = data.balance
  }, () => {}).finally(() => { loading.value = false })
}

function goProblem (problemID) {
  router.push({ name: 'problem-details', params: { problemID } })
}

onMounted(() => load(1))
</script>

<style lang="less" scoped>
.coins {
  max-width: 860px;
  margin: 0 auto;
}
.summary {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px 40px;
  padding-bottom: 20px;
  border-bottom: 1px solid #ebeef5;
}
.balance {
  display: flex;
  align-items: baseline;
  gap: 6px;
  .num {
    font-size: 40px;
    font-weight: 700;
    color: #b57b07;
    font-variant-numeric: tabular-nums;
  }
  .unit {
    color: #606266;
  }
}
.ways {
  margin: 0;
  padding-left: 18px;
  color: #606266;
  font-size: 14px;
  line-height: 1.8;
}
.plus {
  color: var(--el-color-success);
  font-weight: 600;
}
.minus {
  color: var(--el-color-danger);
  font-weight: 600;
}
</style>
