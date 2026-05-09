import * as Blockly from "blockly";
import { pythonGenerator, Order } from "blockly/python";

// ============================================
// 리스트 카테고리 커스텀 블록
// ============================================

// 텍스트를 분리하기
Blockly.Blocks["text_split"] = {
  init: function () {
    this.jsonInit({
      message0: "%1 을(를) %2 (으)로 분리하기",
      args0: [
        { type: "input_value", name: "TXT", check: "String" },
        { type: "input_value", name: "SEP", check: "String" },
      ],
      inputsInline: true,
      output: "Array",
      style: "list_blocks",
      tooltip: "텍스트를 분리하여 리스트로 만듭니다.",
      helpUrl: "",
    });
  },
};
pythonGenerator.forBlock["text_split"] = function (block, generator) {
  const text = generator.valueToCode(block, "TXT", Order.MEMBER) || "''";
  const separator = generator.valueToCode(block, "SEP", Order.NONE) || "''";
  const code = `${text}.split(${separator !== "''" ? separator : ""})`;
  return [code, Order.FUNCTION_CALL];
};

// 리스트 값을 모두 숫자로 바꾸기
Blockly.Blocks["list_map_number"] = {
  init: function () {
    this.jsonInit({
      message0: "%1 의 모든 값을 %2 로 변환하기",
      args0: [
        { type: "input_value", name: "LIST", check: "Array" },
        {
          type: "field_dropdown",
          name: "TYPE",
          options: [
            ["정수", "int"],
            ["실수", "float"],
          ],
        },
      ],
      inputsInline: true,
      output: "Array",
      style: "list_blocks",
      tooltip: "리스트 안의 모든 값을 지정한 숫자 형태로 바꿉니다.",
      helpUrl: "",
    });
  },
};
pythonGenerator.forBlock["list_map_number"] = function (block, generator) {
  const li = generator.valueToCode(block, "LIST", Order.NONE) || "[]";
  const type = block.getFieldValue("TYPE");
  const code = `list(map(${type}, ${li}))`;
  return [code, Order.FUNCTION_CALL];
};

// 리스트 데이터수
Blockly.Blocks["lists_length"] = {
  init: function () {
    this.jsonInit({
      message0: "%1 의 데이터수",
      args0: [
        { type: "input_value", name: "VALUE", check: ["String", "Array"] },
      ],
      inputsInline: true,
      output: "Number",
      style: "math_blocks",
      tooltip: "리스트의 데이터수를 구합니다.",
      helpUrl: "",
    });
  },
};

// 리스트 인덱싱
Blockly.Blocks["list_get_nth"] = {
  init: function () {
    this.jsonInit({
      message0: "%1 의 %2 번 값",
      args0: [
        { type: "input_value", name: "LIST", check: "Array" },
        { type: "input_value", name: "INDEX", check: "Number" },
      ],
      inputsInline: true,
      output: null,
      style: "variable_blocks",
      tooltip: "리스트의 특정 위치에 있는 값을 가져옵니다.(첫 번째는 0번)",
      helpUrl: "",
    });
  },
};
pythonGenerator.forBlock["list_get_nth"] = function (block, generator) {
  const list = generator.valueToCode(block, "LIST", Order.MEMBER) || "[]";
  const index = generator.getAdjustedInt(block, "INDEX", 1);
  const code = `${list}[${index}]`;
  return [code, Order.MEMBER];
};

//리스트 값 추가하기
Blockly.Blocks["list_append"] = {
  init: function () {
    this.jsonInit({
      message0: "%1 에 %2 추가하기",
      args0: [
        { type: "input_value", name: "LIST", check: "Array" },
        { type: "input_value", name: "ITEM" },
      ],
      inputsInline: true,
      previousStatement: null,
      nextStatement: null,
      style: "list_blocks",
      tooltip: "리스트의 맨 마지막에 새로운 항목을 추가합니다.",
      helpUrl: "",
    });
  },
};
pythonGenerator.forBlock["list_append"] = function (block, generator) {
  const list = generator.valueToCode(block, "LIST", Order.MEMBER) || "[]";
  const item = generator.valueToCode(block, "ITEM", Order.NONE) || "0";
  return `${list}.append(${item})\n`;
};

// 리스트 값 삭제하기
Blockly.Blocks["list_pop"] = {
  init: function () {
    this.jsonInit({
      message0: "%1 의 마지막 값 삭제하기",
      args0: [{ type: "input_value", name: "LIST", check: "Array" }],
      inputsInline: true,
      previousStatement: null,
      nextStatement: null,
      style: "list_blocks",
      tooltip: "리스트의 맨 마지막 항목을 삭제합니다.",
      helpUrl: "",
    });
  },
};
pythonGenerator.forBlock["list_pop"] = function (block, generator) {
  const list = generator.valueToCode(block, "LIST", Order.MEMBER) || "[]";
  return `${list}.pop()\n`;
};

// 리스트 정렬하기
Blockly.Blocks["list_sort"] = {
  init: function () {
    this.jsonInit({
      message0: "%1 을(를) %2 으로 정렬하기",
      args0: [
        { type: "input_value", name: "LIST", check: "Array" },
        {
          type: "field_dropdown",
          name: "ORDER",
          options: [
            ["오름차순", "ASC"],
            ["내림차순", "DESC"],
          ],
        },
      ],
      inputsInline: true,
      previousStatement: null,
      nextStatement: null,
      style: "list_blocks",
      tooltip: "리스트의 항목들을 순서대로 정렬합니다.",
      helpUrl: "",
    });
  },
};
pythonGenerator.forBlock["list_sort"] = function (block, generator) {
  const list = generator.valueToCode(block, "LIST", Order.MEMBER) || "[]";
  const order = block.getFieldValue("ORDER");
  if (order === "DESC") {
    return `${list}.sort(reverse=True)\n`;
  } else {
    return `${list}.sort()\n`;
  }
};
