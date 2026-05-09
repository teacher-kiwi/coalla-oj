<template>
  <pre v-highlight="code"><code :class="language" :style="styleObject"></code></pre>
</template>

<script setup>
import { reactive, watch } from 'vue'

const props = defineProps({
  language: { type: String, default: '' },
  code: { type: String, required: true },
  borderColor: { type: String, default: 'green' }
})

const styleObject = reactive({
  'border-left': `2px solid ${props.borderColor}`
})

watch(() => props.borderColor, (newVal) => {
  styleObject['border-left'] = `2.5px solid ${newVal}`
})
</script>

<style scoped lang="less">
  pre {
    padding: 0;
    display: block;
    code {
      padding: 20px;
      font-size: 1.1em;
    }
  }
</style>
