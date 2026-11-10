<template>
  <div class="view">
    <Panel title="캐릭터 아이템">
      <template #header>
        <el-radio-group v-model="filter" size="small">
          <el-radio-button value="">전체 {{ items.length }}</el-radio-button>
          <el-radio-button v-for="k in SLOT_KEYS" :key="k" :value="k">
            {{ SLOTS[k].label }} {{ countOf(k) }}
          </el-radio-button>
        </el-radio-group>
      </template>
      <div v-loading="loading" class="body">
        <div class="actions">
          <el-button type="primary" size="small" :icon="Plus"
                     @click="router.push({ name: 'create-avatar-item' })">아이템 만들기</el-button>
          <el-button size="small" :loading="importing" @click="importExamples">예시 아이템 가져오기</el-button>
          <span class="hint">샵에 올린 아이템만 학생에게 보입니다. 산 사람이 있는 아이템은 지우면 샵에서만 내려가고, 산 사람은 계속 입습니다.</span>
        </div>
        <p v-if="!loading && !shown.length" class="empty">
          아직 아이템이 없습니다. '아이템 만들기'로 그리거나, '예시 아이템 가져오기'로 15개를 먼저 넣어 보세요.
        </p>
        <div class="cards">
          <div v-for="r in shown" :key="r.id" :class="['card', { off: !r.visible }]">
            <div class="pic" @click="edit(r)">
              <CharacterAvatar :eq="{ [r.slot]: itemFromRecord(r) }" mode="full" :size="128" />
            </div>
            <strong class="name">{{ r.name }}</strong>
            <span class="kind">
              {{ SLOTS[r.slot].label }}<template v-if="r.variant"> · {{ VARIANT_LABEL[r.variant] }}</template>
              <template v-if="r.designer"> · {{ r.designer }}</template>
            </span>
            <span class="price">{{ r.price }} 코인</span>
            <el-switch v-model="r.visible" size="small" active-text="샵에 올림" @change="toggle(r)" />
            <div class="buttons">
              <el-button size="small" @click="edit(r)">고치기</el-button>
              <el-button size="small" type="danger" plain @click="remove(r)">삭제</el-button>
            </div>
          </div>
        </div>
      </div>
    </Panel>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '@admin/api'
import Panel from '@admin/components/Panel.vue'
import CharacterAvatar from '@oj/components/CharacterAvatar.vue'
import { SLOTS, SLOT_KEYS, VARIANT_LABEL, encodePart, itemFromRecord } from '@/utils/character'
import { exampleItems } from '@/utils/workshop'

const router = useRouter()
const items = ref([])
const loading = ref(false)
const importing = ref(false)
const filter = ref('')

const shown = computed(() => filter.value ? items.value.filter(r => r.slot === filter.value) : items.value)
const countOf = k => items.value.filter(r => r.slot === k).length

function load () {
  loading.value = true
  return api.getAvatarItems().then(res => { items.value = res.data.data }, () => {})
    .finally(() => { loading.value = false })
}

function edit (r) {
  router.push({ name: 'edit-avatar-item', params: { itemId: r.id } })
}

function toggle (r) {
  const { id, name, slot, variant, parts, price, visible, designer } = r
  api.updateAvatarItem({ id, name, slot, variant, parts, price, visible, designer })
    .catch(() => { r.visible = !visible })
}

function remove (r) {
  ElMessageBox.confirm(`'${r.name}'을(를) 지웁니다. 산 사람이 있으면 샵에서만 내립니다.`, '아이템 삭제', { type: 'warning' })
    .then(() => api.deleteAvatarItem(r.id))
    .then(res => {
      if (res.data.data && res.data.data.hidden) ElMessage.info(`'${r.name}'은(는) 산 사람이 있어 샵에서 내리기만 했습니다`)
      return load()
    }).catch(() => {})
}

// 프로토타입의 예시 15개를 '샵에 안 올림'으로 넣는다. 이름이 같은 아이템은 건너뛴다.
// 한 개씩 '완료' 알림이 뜨지 않게 api 대신 axios 를 바로 쓴다.
async function importExamples () {
  const have = new Set(items.value.map(r => r.name))
  const todo = exampleItems().filter(it => !have.has(it.name))
  if (!todo.length) { ElMessage.info('예시 아이템이 이미 모두 있습니다'); return }
  importing.value = true
  let done = 0
  try {
    for (const it of todo) {
      const parts = Object.fromEntries(Object.entries(it.parts).map(([p, a]) => [p, encodePart(a)]))
      const res = await axios.post('admin/avatar_item', {
        name: it.name, slot: it.slot, variant: it.variant, price: it.price, visible: false, designer: '', parts
      })
      if (res.data.error) throw new Error(res.data.data)
      done++
    }
    ElMessage.success(`예시 아이템 ${done}개를 넣었습니다. 확인한 뒤 샵에 올려 주세요`)
  } catch (e) {
    ElMessage.error(`예시를 넣다가 멈췄습니다(${done}개 넣음): ${e.message}`)
  } finally {
    importing.value = false
    load()
  }
}

onMounted(load)
</script>

<style lang="less" scoped>
.body {
  min-height: 200px;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  .hint {
    color: #909399;
    font-size: 13px;
  }
}
.empty {
  color: #909399;
}
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 14px;
}
.card {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  &.off .pic {
    opacity: .55;
  }
  .pic {
    display: flex;
    justify-content: center;
    background: #f5f7fa;
    border-radius: 6px;
    padding: 8px 0;
    cursor: pointer;
  }
  .name {
    font-size: 15px;
  }
  .kind {
    font-size: 12px;
    color: #909399;
  }
  .price {
    color: #b57b07;
    font-weight: 600;
    font-size: 14px;
  }
  .buttons {
    display: flex;
    gap: 6px;
    .el-button + .el-button {
      margin-left: 0;
    }
  }
}
</style>
