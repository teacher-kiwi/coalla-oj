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
import './blockly/setup'

const props = defineProps({
  blocks: { type: String, default: '' }
})

const blocklyDiv = ref(null)
let workspace = null

function initBlockly () {
  workspace = Blockly.inject(blocklyDiv.value, {
    readOnly: true,
    // 보기 화면은 제출 목록 사이사이에 끼어 있다. 휠을 가로채면 페이지가 내려가지 않으니
    // 휠은 페이지에 넘기고, 블록은 끌거나 스크롤바·확대 단추로 본다.
    move: { scrollbars: true, drag: true, wheel: false },
    zoom: {
      controls: true,
      wheel: false,
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
