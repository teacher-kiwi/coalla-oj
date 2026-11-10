import * as Blockly from "blockly";
import { pythonGenerator, Order } from "blockly/python";

// 입출력 카테고리 커스텀 블록

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

// 리스트를 띄어서 한 줄로 출력: print(*리스트)
// [3, 5, 7] 이 "3 5 7" 로 나온다. 채점 문제의 "공백으로 구분해 출력" 에 맞춘 블록이다.
Blockly.Blocks["print_list_spaced"] = {
  init: function () {
    this.jsonInit({
      message0: "리스트 %1 을(를) 띄어서 출력",
      args0: [{ type: "input_value", name: "LIST", check: "Array" }],
      inputsInline: true,
      previousStatement: null,
      nextStatement: null,
      style: "text_blocks",
      tooltip: "리스트의 값들을 한 칸씩 띄어서 한 줄에 출력합니다.",
      helpUrl: "",
    });
  },
};
pythonGenerator.forBlock["print_list_spaced"] = function (block, generator) {
  const list = generator.valueToCode(block, "LIST", Order.NONE) || "[]";
  return `print(*${list})\n`;
};
