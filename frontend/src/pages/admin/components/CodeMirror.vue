<template>
  <codemirror
    :model-value="currentValue"
    :extensions="extensions"
    :style="{ height: 'auto', minHeight: '300px', maxHeight: '1000px' }"
    @update:model-value="onChange"
  />
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { Codemirror } from 'vue-codemirror'
import { EditorView } from '@codemirror/view'
import { cpp } from '@codemirror/lang-cpp'
import { python } from '@codemirror/lang-python'

const props = defineProps({
  modelValue: { type: String, default: '' },
  mode: { type: String, default: 'text/x-csrc' }
})

const emit = defineEmits(['change', 'update:modelValue'])
const currentValue = ref(props.modelValue)

const extensions = computed(() => {
  const base = [EditorView.lineWrapping]
  if (props.mode.includes('python')) base.push(python())
  else base.push(cpp())
  return base
})

function onChange (val) {
  currentValue.value = val
  emit('change', val)
  emit('update:modelValue', val)
}

watch(() => props.modelValue, (val) => {
  if (currentValue.value !== val) currentValue.value = val
})
</script>
