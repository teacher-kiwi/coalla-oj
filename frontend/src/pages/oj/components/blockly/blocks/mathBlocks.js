import * as Blockly from "blockly";
import { pythonGenerator, Order } from "blockly/python";

// ============================================
// 수학 카테고리 커스텀 블록
// ============================================

// 텍스트를 숫자로 변환
Blockly.Blocks["text_to_number"] = {
  init: function () {
    this.jsonInit({
      message0: "%1 을(를) %2 로 변환",
      args0: [
        { type: "input_value", name: "TXT", check: "String" },
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
      output: "Number",
      style: "math_blocks",
      tooltip: "텍스트를 숫자로 변환합니다.",
      helpUrl: "",
    });
  },
};
pythonGenerator.forBlock["text_to_number"] = function (block, generator) {
  const text = generator.valueToCode(block, "TXT", Order.NONE) || "'0'";
  const type = block.getFieldValue("TYPE");
  const code = `${type}(${text})`;
  return [code, Order.FUNCTION_CALL];
};

// 사칙연산
Blockly.Blocks["calc_basic"] = {
  init: function () {
    this.jsonInit({
      message0: "%1 %2 %3",
      args0: [
        { type: "input_value", name: "A", check: "Number" },
        {
          type: "field_dropdown",
          name: "OP",
          options: [
            ["+", "+"],
            ["-", "-"],
            ["×", "*"],
            ["÷", "/"],
          ],
        },
        { type: "input_value", name: "B", check: "Number" },
      ],
      inputsInline: true,
      output: "Number",
      style: "math_blocks",
      tooltip: "사칙연산을 수행합니다.",
      helpUrl: "",
    });
  },
};
pythonGenerator.forBlock["calc_basic"] = function (block, generator) {
  const operator = block.getFieldValue("OP");
  const order =
    operator === "*" || operator === "/"
      ? Order.MULTIPLICATIVE
      : Order.ADDITIVE;
  const a = generator.valueToCode(block, "A", order) || "0";
  const b = generator.valueToCode(block, "B", order) || "0";
  const code = `${a} ${operator} ${b}`;
  return [code, order];
};

// 나누기(몫, 나머지)
Blockly.Blocks["calc_division"] = {
  init: function () {
    this.jsonInit({
      message0: "%1 ÷ %2 의 %3",
      args0: [
        { type: "input_value", name: "A", check: "Number" },
        { type: "input_value", name: "B", check: "Number" },
        {
          type: "field_dropdown",
          name: "MODE",
          options: [
            ["몫", "//"],
            ["나머지", "%"],
          ],
        },
      ],
      inputsInline: true,
      output: "Number",
      style: "math_blocks",
      tooltip: "나눗셈의 몫 또는 나머지를 구합니다.",
      helpUrl: "",
    });
  },
};
pythonGenerator.forBlock["calc_division"] = function (block, generator) {
  const order = Order.MULTIPLICATIVE;
  const a = generator.valueToCode(block, "A", order) || "0";
  const b = generator.valueToCode(block, "B", order) || "1";
  const operator = block.getFieldValue("MODE");
  const code = `${a} ${operator} ${b}`;
  return [code, order];
};

// 리스트 통계(합/최소값/최대값)
Blockly.Blocks["list_stats"] = {
  init: function () {
    this.jsonInit({
      message0: "%1 의 %2",
      args0: [
        { type: "input_value", name: "LIST", check: "Array" },
        {
          type: "field_dropdown",
          name: "OP",
          options: [
            ["합", "SUM"],
            ["최소값", "MIN"],
            ["최대값", "MAX"],
          ],
        },
      ],
      inputsInline: true,
      output: "Number",
      style: "math_blocks",
      tooltip: "리스트의 합, 최소값, 최대값을 구합니다.",
      helpUrl: "",
    });
  },
};
pythonGenerator.forBlock["list_stats"] = function (block, generator) {
  const list = generator.valueToCode(block, "LIST", Order.NONE) || "[]";
  const op = block.getFieldValue("OP");
  let code;
  if (op === "SUM") {
    code = `sum(${list})`;
  } else if (op === "MIN") {
    code = `min(${list})`;
  } else if (op === "MAX") {
    code = `max(${list})`;
  }
  return [code, Order.FUNCTION_CALL];
};
