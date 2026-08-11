<template>
  <el-form>
    <el-form-item label="입력">
      <el-input type="textarea" v-model="input" @change="changeInput" @keyup.enter="changeInput" />
    </el-form-item>
    <el-form-item label="출력" />
    <div v-html="text"></div>
  </el-form>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import katex from 'katex'
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
