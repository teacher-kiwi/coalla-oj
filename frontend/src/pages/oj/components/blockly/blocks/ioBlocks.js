import * as Blockly from "blockly";
import { pythonGenerator, Order } from "blockly/python";

// ============================================
// 입출력 카테고리 커스텀 블록
// ============================================

// 한 줄 입력 받기(텍스트)
Blockly.Blocks["input_readline"] = {
  init: function () {
    this.jsonInit({
      message0: "입력 한 줄 받기",
      inputsInline: true,
      output: "String",
      style: "text_blocks",
      tooltip: "입력값을 읽어옵니다.",
      helpUrl: "",
    });
  },
};
pythonGenerator.forBlock["input_readline"] = function (block, generator) {
  generator.definitions_["fast_io"] = "input = open(0).readline";
  const code = "input().strip()";
  return [code, Order.FUNCTION_CALL];
};
