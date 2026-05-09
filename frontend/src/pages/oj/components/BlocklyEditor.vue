<template>
  <div class="blockly-wrapper">
    <el-row type="flex" justify="space-between" class="header">
      <el-col :span="12">
        <div>
          <span>{{ t('m.Language') }}:</span>
          <el-select :model-value="'Block Coding'" @change="onLangChange" class="adjust">
            <el-option value="Block Coding" :label="t('m.Block_Coding')" />
            <el-option v-for="item in languages" :key="item" :value="item" :label="item" />
          </el-select>

          <el-tooltip :content="t('m.Show_Generated_Code')" placement="top">
            <el-button :icon="Document" class="action-btn" @click="showCode = !showCode" />
          </el-tooltip>
        </div>
      </el-col>
      <el-col :span="12">
        <div class="fl-right">
          <el-button type="primary" :icon="Delete" @click="clearWorkspace">초기화</el-button>
        </div>
      </el-col>
    </el-row>

    <div ref="blocklyDiv" class="blockly-container"></div>

    <div v-if="showCode" class="code-preview">
      <div class="code-header">
        <span>{{ t('m.Convert_to_Code') }} (Python)</span>
      </div>
      <pre>{{ generatedCode }}</pre>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessageBox } from 'element-plus'
import { Document, Delete } from '@element-plus/icons-vue'
import * as Blockly from 'blockly'
import 'blockly/blocks'
import * as Ko from 'blockly/msg/ko'
import { pythonGenerator } from 'blockly/python'
import './blockly/blocks'
import { toolboxConfig } from './blockly/toolbox'

const props = defineProps({
  initialBlocks: { type: String, default: '' },
  languages: { type: Array, default: () => [] }
})
const emit = defineEmits(['input', 'update:code', 'update:blocks', 'changeLang'])
const { t } = useI18n()

const blocklyDiv = ref(null)
const showCode = ref(false)
const generatedCode = ref('')
let workspace = null

function updateCode (event) {
  if (event && (event.type === Blockly.Events.UI || event.type === Blockly.Events.DRAG)) return
  generatedCode.value = pythonGenerator.workspaceToCode(workspace)
  emit('input', generatedCode.value)
  emit('update:code', generatedCode.value)
  const jsonState = Blockly.serialization.workspaces.save(workspace)
  emit('update:blocks', JSON.stringify(jsonState))
}

function clearWorkspace () {
  ElMessageBox.confirm('작업 공간을 초기화하시겠습니까?', '확인').then(() => {
    workspace.clear()
    generatedCode.value = ''
    emit('input', '')
  }).catch(() => {})
}

function onLangChange (newLang) {
  emit('changeLang', newLang)
}

function initBlockly () {
  Blockly.setLocale(Ko)
  Blockly.Msg['TEXT_JOIN_TITLE_CREATEWITH'] = '텍스트 합치기'
  Blockly.Msg['TEXT_CREATE_JOIN_TITLE_JOIN'] = '합치기'
  Blockly.Msg['LOGIC_NEGATE_TITLE'] = '%1이(가) 아닙니다.'

  workspace = Blockly.inject(blocklyDiv.value, {
    toolbox: toolboxConfig,
    grid: { spacing: 20, length: 3, colour: '#ccc', snap: true },
    zoom: {
      controls: true,
      wheel: true,
      startScale: 1.0,
      maxScale: 3,
      minScale: 0.3,
      scaleSpeed: 1.2
    },
    trashcan: true,
    renderer: 'thrasos'
  })

  if (props.initialBlocks) {
    try {
      const state = JSON.parse(props.initialBlocks)
      Blockly.serialization.workspaces.load(state, workspace)
    } catch (e) {
      console.warn('블록 상태 로드 실패:', e)
    }
  }

  workspace.addChangeListener(updateCode)
  updateCode()
}

onMounted(initBlockly)
onBeforeUnmount(() => {
  if (workspace) workspace.dispose()
})
</script>

<style lang="less" scoped>
.blockly-wrapper {
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

.blockly-container {
  height: 480px;
  width: 100%;
}

.code-preview {
  margin-top: 15px;
  border: 1px solid #dcdee2;
  border-radius: 4px;
  overflow: hidden;

  .code-header {
    background: #f8f8f9;
    padding: 10px 15px;
    border-bottom: 1px solid #dcdee2;
    font-weight: 500;
  }

  pre {
    margin: 0;
    padding: 15px;
    background: #f8f8f9;
    max-height: 300px;
    overflow-y: auto;
    font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
    font-size: 13px;
    line-height: 1.6;
  }
}
</style>
