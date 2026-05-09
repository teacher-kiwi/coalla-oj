<template>
  <div style="margin: 0px 0px 15px 0px">
    <Row type="flex" justify="space-between" class="header">
      <Col :span="12">
        <div>
          <span>{{ $t("m.Language") }}:</span>
          <Select
            :value="'Block Coding'"
            @on-change="onLangChange"
            class="adjust"
            style="width: 150px; margin-left: 10px"
          >
            <Option value="Block Coding">
              <Icon type="cube"></Icon> {{ $t("m.Block_Coding") }}
            </Option>
            <Option v-for="item in languages" :key="item" :value="item">{{
              item
            }}</Option>
          </Select>

          <Tooltip
            :content="$t('m.Show_Generated_Code')"
            placement="top"
            style="margin-left: 10px"
          >
            <Button icon="code" @click="showCode = !showCode"></Button>
          </Tooltip>
        </div>
      </Col>
      <Col :span="12">
        <div class="fl-right">
          <Button type="primary" @click="clearWorkspace">
            <Icon type="trash-a"></Icon>
            초기화
          </Button>
        </div>
      </Col>
    </Row>

    <!-- Blockly Workspace -->
    <div ref="blocklyDiv" style="height: 480px; width: 100%"></div>

    <!-- Generated Code Preview -->
    <div v-if="showCode" class="code-preview">
      <div class="code-header">
        <span>{{ $t("m.Convert_to_Code") }} (Python)</span>
      </div>
      <pre>{{ generatedCode }}</pre>
    </div>
  </div>
</template>

<script>
import Blockly from "blockly";
import "blockly/blocks";
import Ko from "blockly/msg/ko";
import { pythonGenerator } from "blockly/python";
import "./blockly/blocks";
import { toolboxConfig } from "./blockly/toolbox";

export default {
  name: "BlocklyEditor",
  props: {
    initialBlocks: {
      type: String,
      default: "",
    },
    languages: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      workspace: null,
      showCode: false,
      generatedCode: "",
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
  computed: {
    toolbox() {
      return toolboxConfig;
    },
  },
  methods: {
    initBlockly() {
      Blockly.setLocale(Ko);
      // =========================================================
      // 블록 텍스트 변경
      Blockly.Msg["TEXT_JOIN_TITLE_CREATEWITH"] = "텍스트 합치기";
      Blockly.Msg["TEXT_CREATE_JOIN_TITLE_JOIN"] = "합치기";
      Blockly.Msg["LOGIC_NEGATE_TITLE"] = "%1이(가) 아닙니다.";
      // =========================================================

      // Create workspace
      this.workspace = Blockly.inject(this.$refs.blocklyDiv, {
        toolbox: this.toolbox,
        grid: { spacing: 20, length: 3, colour: "#ccc", snap: true },
        zoom: {
          controls: true,
          wheel: true,
          startScale: 1.0,
          maxScale: 3,
          minScale: 0.3,
          scaleSpeed: 1.2,
        },
        trashcan: true,
        renderer: "thrasos",
      });

      // JSON 기반으로 블록 불러오기
      if (this.initialBlocks) {
        try {
          const state = JSON.parse(this.initialBlocks);
          Blockly.serialization.workspaces.load(state, this.workspace);
        } catch (e) {
          console.warn("블록 상태 로드 실패:", e);
        }
      }

      // Listen to changes
      this.workspace.addChangeListener(this.updateCode);
      this.updateCode();
    },

    updateCode(event) {
      if (
        event &&
        (event.type === Blockly.Events.UI || event.type === Blockly.Events.DRAG)
      ) {
        return;
      }

      this.generatedCode = pythonGenerator.workspaceToCode(this.workspace);

      // Emit code to parent
      this.$emit("input", this.generatedCode);
      this.$emit("update:code", this.generatedCode);

      // Save workspace state
      const jsonState = Blockly.serialization.workspaces.save(this.workspace);
      const jsonString = JSON.stringify(jsonState);
      this.$emit("update:blocks", jsonString);
    },

    clearWorkspace() {
      this.$Modal.confirm({
        title: "확인",
        content: "작업 공간을 초기화하시겠습니까?",
        onOk: () => {
          this.workspace.clear();
          this.generatedCode = "";
          this.$emit("input", "");
        },
      });
    },

    onLangChange(newLang) {
      this.$emit("changeLang", newLang);
    },

    getCode() {
      return this.generatedCode;
    },
  },
};
</script>

<style lang="less" scoped>
.header {
  margin: 5px 5px 15px 5px;
  .fl-right {
    float: right;
  }
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
    font-family: "Monaco", "Menlo", "Consolas", monospace;
    font-size: 13px;
    line-height: 1.6;
  }
}
</style>
