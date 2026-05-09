<template>
  <MdEditor
    v-model="currentValue"
    :language="mdEditorLang"
    :toolbars-exclude="['github']"
    :preview="false"
    :footers="[]"
    style="height: 400px"
    @on-change="onChange"
  />
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { MdEditor } from 'md-editor-v3'
import 'md-editor-v3/lib/style.css'

const { locale } = useI18n()

const mdEditorLang = computed(() => {
  if (locale.value.startsWith('zh')) return 'zh-CN'
  return 'en-US'
})

const props = defineProps({
  value: { type: String, default: '' },
  toolbar: { type: Array, default: () => [] }
})

const emit = defineEmits(['change', 'input', 'update:value'])
const currentValue = ref(props.value)

function onChange (val) {
  emit('change', val)
  emit('input', val)
  emit('update:value', val)
}

watch(() => props.value, (val) => {
  if (currentValue.value !== val) currentValue.value = val
})

watch(currentValue, (val) => {
  emit('change', val)
  emit('input', val)
  emit('update:value', val)
})
</script>
