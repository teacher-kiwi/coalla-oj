import * as Blockly from "blockly";
import { pythonGenerator, Order } from "blockly/python";

// ============================================
// 문자열 카테고리 커스텀 블록
// ============================================
// 추가 문자열 관련 커스텀 블록을 여기에 작성하세요

// 텍스트 인덱싱
Blockly.Blocks["text_get_nth"] = {
  init: function () {
    this.jsonInit({
      message0: "%1 의 %2 번 글자",
      args0: [
        { type: "input_value", name: "TXT", check: "String" },
        { type: "input_value", name: "INDEX", check: "Number" },
      ],
      inputsInline: true,
      output: "String",
      style: "text_blocks",
      tooltip: "텍스트의 특정 위치에 있는 값을 가져옵니다.(첫 번째는 0번)",
      helpUrl: "",
    });
  },
};
pythonGenerator.forBlock["text_get_nth"] = function (block, generator) {
  const txt = generator.valueToCode(block, "TXT", Order.MEMBER) || "''";
  const index = generator.getAdjustedInt(block, "INDEX", 1);
  const code = `${txt}[${index}]`;
  return [code, Order.MEMBER];
};

// 텍스트 길이
Blockly.Blocks["text_length"] = {
  init: function () {
    this.jsonInit({
      message0: "%1 의 글자수",
      args0: [
        { type: "input_value", name: "VALUE", check: ["String", "Array"] },
      ],
      inputsInline: true,
      output: "Number",
      style: "math_blocks",
      tooltip: "텍스트의 글자수를 구합니다.",
      helpUrl: "",
    });
  },
};
