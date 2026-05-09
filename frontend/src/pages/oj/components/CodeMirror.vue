<template>
  <div class="code-editor-wrapper">
    <el-row type="flex" justify="space-between" class="header">
      <el-col :span="12">
        <div>
          <span>{{ t('m.Language') }}:</span>
          <el-select :model-value="language" @change="onLangChange" class="adjust">
            <el-option v-if="languages.includes('Python3')" value="Block Coding" :label="t('m.Block_Coding')" />
            <el-option v-for="item in languages" :key="item" :value="item" :label="item" />
          </el-select>

          <el-tooltip :content="t('m.Reset_to_default_code_definition')" placement="top">
            <el-button :icon="Refresh" class="action-btn" @click="onResetClick" />
          </el-tooltip>

          <el-tooltip :content="t('m.Upload_file')" placement="top">
            <el-button :icon="Upload" class="action-btn" @click="onUploadFile" />
          </el-tooltip>

          <input type="file" ref="fileInputRef" class="file-input" @change="onUploadFileDone" />
        </div>
      </el-col>
      <el-col :span="12">
        <div class="fl-right">
          <span>{{ t('m.Theme') }}:</span>
          <el-select :model-value="theme" @change="onThemeChange" class="adjust">
            <el-option v-for="item in themes" :key="item.value" :value="item.value" :label="item.label" />
          </el-select>
        </div>
      </el-col>
    </el-row>
    <codemirror
      :model-value="value"
      :extensions="extensions"
      :style="{ height: 'auto', minHeight: '300px', maxHeight: '1000px' }"
      @update:model-value="onEditorCodeChange"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Codemirror } from 'vue-codemirror'
import { EditorView } from '@codemirror/view'
import { cpp } from '@codemirror/lang-cpp'
import { python } from '@codemirror/lang-python'
import { java } from '@codemirror/lang-java'
import { javascript } from '@codemirror/lang-javascript'
import { oneDark } from '@codemirror/theme-one-dark'
import { Refresh, Upload } from '@element-plus/icons-vue'
import utils from '@/utils/utils'

const props = defineProps({
  value: { type: String, default: '' },
  languages: { type: Array, default: () => ['C', 'C++', 'Java', 'Python2'] },
  language: { type: String, default: 'C++' },
  theme: { type: String, default: 'solarized' }
})

const emit = defineEmits(['update:value', 'changeLang', 'changeTheme', 'resetCode'])

const { t } = useI18n()
const fileInputRef = ref(null)

const themes = computed(() => [
  { label: t('m.Monokai'), value: 'monokai' },
  { label: t('m.Solarized_Light'), value: 'solarized' },
  { label: t('m.Material'), value: 'material' }
])

function langExtension (name) {
  if (name === 'Python2' || name === 'Python3') return python()
  if (name === 'Java') return java()
  if (name === 'JavaScript') return javascript()
  return cpp()
}

const extensions = computed(() => {
  const base = [EditorView.lineWrapping, langExtension(props.language)]
  if (props.theme === 'monokai' || props.theme === 'material') base.push(oneDark)
  return base
})

function onEditorCodeChange (newCode) {
  emit('update:value', newCode)
}
function onLangChange (newVal) {
  emit('changeLang', newVal)
}
function onThemeChange (newTheme) {
  emit('changeTheme', newTheme)
}
function onResetClick () {
  emit('resetCode')
}
function onUploadFile () {
  fileInputRef.value?.click()
}
function onUploadFileDone (e) {
  const f = e.target.files[0]
  if (!f) return
  const fr = new window.FileReader()
  fr.onload = (evt) => {
    emit('update:value', evt.target.result)
    if (fileInputRef.value) fileInputRef.value.value = ''
  }
  fr.readAsText(f, 'UTF-8')
}

onMounted(() => {
  utils.getLanguages()
})

watch(() => props.theme, () => {})
</script>

<style lang="less" scoped>
  .code-editor-wrapper {
    margin: 0 0 15px 0;
  }

  .header {
    margin: 5px 5px 15px 5px;
    .adjust {
      width: 150px;
      margin-left: 10px;
    }
    .fl-right {
      float: right;
    }
  }

  .action-btn {
    margin-left: 10px;
  }

  .file-input {
    display: none;
  }
</style>
