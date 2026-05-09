<template>
  <div class="blockly-viewer">
    <div class="viewer-header">
      <Icon type="cube"></Icon>
      <span>블록 코드</span>
    </div>
    <div ref="blocklyDiv" class="blockly-container"></div>
  </div>
</template>

<script>
import Blockly from "blockly";
import "blockly/blocks";
import Ko from "blockly/msg/ko";
import "./blockly/blocks";

export default {
  name: "BlocklyViewer",
  props: {
    blocks: {
      type: String,
      default: "",
    },
  },
  data() {
    return {
      workspace: null,
    };
  },
  mounted() {
    this.initBlockly();
  },
  beforeDestroy() {
    if (this.workspace) {
      this.workspace.dispose();
    }
  },
  methods: {
    initBlockly() {
      Blockly.setLocale(Ko);
      Blockly.Msg["TEXT_JOIN_TITLE_CREATEWITH"] = "텍스트 합치기";
      Blockly.Msg["TEXT_CREATE_JOIN_TITLE_JOIN"] = "합치기";
      Blockly.Msg["LOGIC_NEGATE_TITLE"] = "%1이(가) 아닙니다.";

      this.workspace = Blockly.inject(this.$refs.blocklyDiv, {
        readOnly: true,
        scrollbars: true,
        zoom: {
          controls: true,
          wheel: true,
          startScale: 0.9,
          maxScale: 3,
          minScale: 0.3,
          scaleSpeed: 1.2,
        },
        renderer: "thrasos",
      });

      if (this.blocks) {
        try {
          const state = JSON.parse(this.blocks);
          Blockly.serialization.workspaces.load(state, this.workspace);
        } catch (e) {
          console.warn("블록 상태 로드 실패:", e);
        }
      }
    },
  },
  watch: {
    blocks(newVal) {
      if (this.workspace && newVal) {
        try {
          this.workspace.clear();
          const state = JSON.parse(newVal);
          Blockly.serialization.workspaces.load(state, this.workspace);
        } catch (e) {
          console.warn("블록 상태 로드 실패:", e);
        }
      }
    },
  },
};
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
