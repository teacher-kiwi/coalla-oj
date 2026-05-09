<template>
  <div class="blockly-viewer">
    <div class="viewer-header">
      <el-icon><Box /></el-icon>
      <span>블록 코드</span>
    </div>
    <div ref="blocklyDiv" class="blockly-container"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { Box } from '@element-plus/icons-vue'
import * as Blockly from 'blockly'
import 'blockly/blocks'
import * as Ko from 'blockly/msg/ko'
import './blockly/blocks'

const props = defineProps({
  blocks: { type: String, default: '' }
})

const blocklyDiv = ref(null)
let workspace = null

function initBlockly () {
  Blockly.setLocale(Ko)
  Blockly.Msg['TEXT_JOIN_TITLE_CREATEWITH'] = '텍스트 합치기'
  Blockly.Msg['TEXT_CREATE_JOIN_TITLE_JOIN'] = '합치기'
  Blockly.Msg['LOGIC_NEGATE_TITLE'] = '%1이(가) 아닙니다.'

  workspace = Blockly.inject(blocklyDiv.value, {
    readOnly: true,
    scrollbars: true,
    zoom: {
      controls: true,
      wheel: true,
      startScale: 0.9,
      maxScale: 3,
      minScale: 0.3,
      scaleSpeed: 1.2
    },
    renderer: 'thrasos'
  })

  if (props.blocks) {
    try {
      const state = JSON.parse(props.blocks)
      Blockly.serialization.workspaces.load(state, workspace)
    } catch (e) {
      console.warn('블록 상태 로드 실패:', e)
    }
  }
}

onMounted(initBlockly)
onBeforeUnmount(() => {
  if (workspace) workspace.dispose()
})

watch(() => props.blocks, (newVal) => {
  if (workspace && newVal) {
    try {
      workspace.clear()
      const state = JSON.parse(newVal)
      Blockly.serialization.workspaces.load(state, workspace)
    } catch (e) {
      console.warn('블록 상태 로드 실패:', e)
    }
  }
})
</script>

<style lang="less" scoped>
.blockly-viewer {
  border: 1px solid #dcdee2;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 15px;

  .viewer-header {
    background: #f8f8f9;
    padding: 10px 15px;
    border-bottom: 1px solid #dcdee2;
    font-weight: 500;

    span {
      margin-left: 8px;
    }
  }

  .blockly-container {
    height: 400px;
    width: 100%;
  }
}
</style>
