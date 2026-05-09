<template>
  <el-form>
    <el-form-item :label="t('m.Input')">
      <el-input type="textarea" v-model="input" @change="changeInput" @keyup.enter="changeInput" />
    </el-form-item>
    <el-form-item :label="t('m.Output')" />
    <div v-html="text"></div>
  </el-form>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import katex from 'katex'

const { t } = useI18n()
const input = ref('c = \\pm\\sqrt{a^2 + b^2}')
const text = ref('')

function renderTex (data) {
  return katex.renderToString(data, { displayMode: true, throwOnError: false })
}

function changeInput () {
  try {
    text.value = renderTex(input.value)
  } catch (e) {
    text.value = '<p style="text-align: center"><span style="color:red">Error Input</span></p>'
  }
}

onMounted(() => {
  text.value = renderTex(input.value)
})
</script>
