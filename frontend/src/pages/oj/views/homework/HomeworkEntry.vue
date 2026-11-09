<template>
  <div class="hw-entry">
    <el-card class="entry-card">
      <p class="kicker">코알라 OJ</p>
      <h2>바로 과제</h2>
      <p class="hint">선생님께 받은 6자리 숫자를 넣으세요.<br>계정이 없어도 됩니다.</p>
      <form @submit.prevent="go">
        <el-input v-model="code" maxlength="6" inputmode="numeric" placeholder="000000"
                  size="large" class="code-input" autofocus />
        <el-button type="primary" size="large" native-type="submit" :disabled="!valid" class="go">
          들어가기
        </el-button>
      </form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const code = ref('')
const valid = computed(() => /^\d{6}$/.test(code.value.trim()))

function go () {
  if (!valid.value) return
  router.push({ name: 'homework-home', params: { code: code.value.trim() } })
}
</script>

<style lang="less" scoped>
.hw-entry {
  display: flex;
  justify-content: center;
  padding-top: 8vh;
}
.entry-card {
  width: 100%;
  max-width: 420px;
  text-align: center;
  border-top: 4px solid var(--el-color-primary);
  :deep(.el-card__body) {
    padding: 32px 28px;
  }
  .kicker {
    margin: 0;
    font-size: 13px;
    color: var(--el-color-primary);
    font-weight: 600;
  }
  h2 {
    margin: 4px 0 8px;
    font-size: 26px;
  }
  .hint {
    color: #909399;
    margin: 0 0 24px;
    line-height: 1.6;
  }
  form {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .code-input :deep(input) {
    text-align: center;
    height: 56px;
    font-size: 28px;
    font-weight: 600;
    letter-spacing: 8px;
  }
}
</style>
