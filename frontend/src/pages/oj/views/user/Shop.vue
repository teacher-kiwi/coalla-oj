<template>
  <div class="shop">
    <Panel shadow>
      <template #title>캐릭터 샵</template>
      <div v-loading="loading" class="layout">
        <!-- 왼쪽: 입어보는 모습 -->
        <aside class="stage panel-inset">
          <div class="figure">
            <CharacterAvatar v-if="username" :username="username" :eq="tryEq" mode="full" :size="192" animate />
          </div>
          <div class="balance">
            <span class="num">{{ balance }}</span> 코인
            <router-link class="link-text history" :to="{ name: 'coins' }">내역</router-link>
          </div>
          <p class="hint">
            아이템을 누르면 입어 봐요. 다시 누르면 벗어요.
          </p>
          <template v-if="changed">
            <p v-if="unownedTried.length" class="hint warn">
              아직 안 산 아이템:
              <span v-for="r in unownedTried" :key="r.id" class="tag">{{ r.name }}({{ r.price }})</span>
              <br>사거나 벗어야 이대로 입을 수 있어요.
            </p>
            <div class="stage-buttons">
              <el-button @click="reset">원래대로</el-button>
              <el-button type="primary" :disabled="unownedTried.length > 0" :loading="saving" @click="wear">
                이대로 입기
              </el-button>
            </div>
          </template>
        </aside>

        <!-- 오른쪽: 아이템 목록 -->
        <section class="list">
          <div class="filters">
            <el-radio-group v-model="slot" size="small">
              <el-radio-button value="">전체</el-radio-button>
              <el-radio-button v-for="k in slotsWithItems" :key="k" :value="k">{{ SLOTS[k].label }}</el-radio-button>
            </el-radio-group>
            <el-checkbox v-model="mineOnly" size="small">내 아이템만</el-checkbox>
          </div>
          <p v-if="!canBuy" class="hint warn">이 계정으로는 아이템을 살 수 없어요.</p>
          <p v-if="!loading && !shown.length" class="empty">
            {{ items.length ? '조건에 맞는 아이템이 없어요' : '아직 샵에 올라온 아이템이 없어요. 곧 채워질 거예요!' }}
          </p>
          <div class="cards">
            <div v-for="r in shown" :key="r.id"
                 :class="['card', { trying: tryOn[r.slot] === r.id }]"
                 role="button" tabindex="0" :aria-pressed="tryOn[r.slot] === r.id"
                 @click="toggle(r)" @keydown.enter.prevent="toggle(r)" @keydown.space.prevent="toggle(r)">
              <div class="pic">
                <CharacterAvatar :username="username" :eq="{ [r.slot]: drawable(r.id) }" mode="full" :size="112" />
                <span v-if="equipped[r.slot] === r.id" class="badge on">입는 중</span>
                <span v-else-if="tryOn[r.slot] === r.id" class="badge">입어보는 중</span>
              </div>
              <strong class="name">{{ r.name }}</strong>
              <span class="kind">
                {{ SLOTS[r.slot].label }}<template v-if="r.slot === 'bottom' || r.slot === 'shoes'"> · {{ VARIANT_LABEL[r.variant] }}</template>
                <template v-if="r.designer"> · {{ r.designer }}</template>
              </span>
              <span v-if="owned.has(r.id)" class="owned">가지고 있어요</span>
              <el-button v-else size="small" type="warning" plain class="buy"
                         :disabled="!canBuy || balance < r.price" :loading="buying === r.id"
                         @click.stop="buy(r)">
                {{ r.price ? `${r.price} 코인에 사기` : '무료로 받기' }}
              </el-button>
            </div>
          </div>
        </section>
      </div>
    </Panel>
  </div>
</template>

<script setup>
// 캐릭터 샵. 아이템을 눌러 입어 보고, 코인으로 사고, 가진 아이템으로 한 벌을 골라 입는다.
// 사면 바로 입는다(서버가 같은 자리의 옷을 벗긴다).
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@oj/api'
import Panel from '@oj/components/Panel.vue'
import CharacterAvatar from '@oj/components/CharacterAvatar.vue'
import { SLOTS, SLOT_KEYS, VARIANT_LABEL, itemFromRecord } from '@/utils/character'
import { setLook } from '@/utils/looks'
import { useUserStore } from '@/store/user'

const userStore = useUserStore()
const username = computed(() => userStore.user.username || '')

const loading = ref(false)
const saving = ref(false)
const buying = ref(0)
const items = ref([])
const owned = ref(new Set())
const equipped = ref({})
const tryOn = ref({})
const balance = ref(userStore.coins)
const canBuy = ref(true)
const slot = ref('')
const mineOnly = ref(false)

const byId = computed(() => new Map(items.value.map(r => [r.id, r])))
const drawables = computed(() => new Map(items.value.map(r => [r.id, itemFromRecord(r)])))
const drawable = id => drawables.value.get(id)

const slotsWithItems = computed(() => SLOT_KEYS.filter(k => items.value.some(r => r.slot === k)))
const shown = computed(() => items.value.filter(r =>
  (!slot.value || r.slot === slot.value) && (!mineOnly.value || owned.value.has(r.id))))

const tryEq = computed(() => {
  const eq = {}
  for (const [k, id] of Object.entries(tryOn.value)) if (drawable(id)) eq[k] = drawable(id)
  return eq
})
const sameOutfit = (a, b) => SLOT_KEYS.every(k => (a[k] || null) === (b[k] || null))
const changed = computed(() => !sameOutfit(tryOn.value, equipped.value))
const unownedTried = computed(() => Object.values(tryOn.value)
  .filter(id => !owned.value.has(id)).map(id => byId.value.get(id)).filter(Boolean))

function apply (data) {
  items.value = data.items
  owned.value = new Set(data.owned)
  equipped.value = { ...data.equipped }
  tryOn.value = { ...data.equipped }
  balance.value = data.balance
  canBuy.value = data.can_buy
  userStore.setCoins(data.balance)
}

function load () {
  loading.value = true
  api.getShop().then(res => apply(res.data.data), () => {})
    .finally(() => { loading.value = false })
}

function toggle (r) {
  const next = { ...tryOn.value }
  if (next[r.slot] === r.id) delete next[r.slot]
  else next[r.slot] = r.id
  tryOn.value = next
}

function reset () {
  tryOn.value = { ...equipped.value }
}

function afterWear (eq) {
  equipped.value = { ...eq }
  setLook(username.value, eq, items.value.filter(r => Object.values(eq).includes(r.id)))
}

function buy (r) {
  const what = r.price ? `${r.price} 코인에 살까요?` : '무료로 받을까요?'
  ElMessageBox.confirm(`'${r.name}'을(를) ${what} 사면 바로 입어요.`, '아이템 사기',
    { confirmButtonText: '살게요', cancelButtonText: '그만두기' })
    .then(() => {
      buying.value = r.id
      return api.buyAvatarItem(r.id)
    })
    .then(res => {
      const data = res.data.data
      owned.value = new Set([...owned.value, r.id])
      balance.value = data.balance
      userStore.setCoins(data.balance)
      // 입어 보던 다른 자리는 그대로 두고, 산 자리는 산 아이템으로
      tryOn.value = { ...tryOn.value, [r.slot]: r.id }
      afterWear(data.equipped)
      ElMessage.success(`'${r.name}'을(를) 샀어요!`)
    })
    .catch(() => {})
    .finally(() => { buying.value = 0 })
}

function wear () {
  saving.value = true
  const equip = Object.fromEntries(SLOT_KEYS.map(k => [k, tryOn.value[k] || null]))
  api.equipAvatar(equip).then(res => {
    afterWear(res.data.data.equipped)
    tryOn.value = { ...equipped.value }
    ElMessage.success('새 모습으로 입었어요')
  }, () => {}).finally(() => { saving.value = false })
}

onMounted(load)
</script>

<style lang="less" scoped>
.shop {
  max-width: 1100px;
  margin: 0 auto;
}
.layout {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: 24px;
  align-items: start;
  min-height: 300px;
}
@media (max-width: 767px) {
  .layout {
    grid-template-columns: minmax(0, 1fr);
  }
}
.stage {
  position: sticky;
  top: 80px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  text-align: center;
  .figure {
    width: 208px;
    height: 208px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    background: #fff;
    border: 1px solid #ebeef5;
  }
  .balance {
    color: #606266;
    .num {
      font-size: 28px;
      font-weight: 700;
      color: #b57b07;
      font-variant-numeric: tabular-nums;
    }
    .history {
      margin-left: 8px;
      font-size: 13px;
    }
  }
  .stage-buttons {
    display: flex;
    gap: 8px;
    .el-button + .el-button {
      margin-left: 0;
    }
  }
}
.hint {
  margin: 0;
  color: #909399;
  font-size: 13px;
  line-height: 1.6;
  &.warn {
    color: #b57b07;
  }
  .tag {
    margin-right: 6px;
    font-weight: 600;
  }
}
.filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 16px;
  margin-bottom: 14px;
}
.empty {
  color: #909399;
}
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 12px;
}
.card {
  border: 2px solid #ebeef5;
  border-radius: 8px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  cursor: pointer;
  transition: border-color .15s;
  &:hover,
  &:focus-visible {
    border-color: var(--el-color-primary-light-5);
    outline: none;
  }
  &.trying {
    border-color: var(--el-color-primary);
  }
  .pic {
    position: relative;
    display: flex;
    justify-content: center;
    background: #f5f7fa;
    border-radius: 6px;
    padding: 6px 0;
  }
  .badge {
    position: absolute;
    top: 6px;
    left: 6px;
    padding: 1px 6px;
    border-radius: 10px;
    font-size: 11px;
    background: var(--el-color-primary-light-8);
    color: var(--el-color-primary);
    &.on {
      background: var(--el-color-success-light-8);
      color: var(--el-color-success);
    }
  }
  .name {
    font-size: 14px;
  }
  .kind {
    font-size: 12px;
    color: #909399;
  }
  .owned {
    font-size: 13px;
    color: var(--el-color-success);
    font-weight: 600;
    line-height: 24px;
  }
  .buy {
    align-self: stretch;
  }
}
</style>
