import * as Blockly from "blockly";
import { pythonGenerator, Order } from "blockly/python";

// 딕셔너리(맵) 카테고리 블록
//
// 키로 값을 찾는 자료. 개수 세기에 많이 쓴다: 승리[손] += 1
// 값을 넣거나 바꿀 때는 따로 블록을 두지 않고 '설정'·'바꾸기' 블록 앞 칸에 '키의 값' 블록을 끼운다.
// 연결 검사: 빈 딕셔너리 블록만 "Dict" 를 내보내고, 변수 블록은 검사가 없어 어디든 들어간다.

// 빈 딕셔너리 → {}
Blockly.Blocks["dict_create_empty"] = {
  init: function () {
    this.jsonInit({
      message0: "빈 딕셔너리",
      output: "Dict",
      style: "list_blocks",
      tooltip: "키와 값을 짝지어 담을 빈 딕셔너리를 만듭니다. 다른 언어에서는 맵이라고도 부릅니다.",
      helpUrl: "",
    });
  },
};
pythonGenerator.forBlock["dict_create_empty"] = function () {
  return ["{}", Order.ATOMIC];
};

// [d] 에서 키 [k] 의 값 → d[k]
// 키가 없으면 실행 오류(KeyError)가 난다. 없을 수도 있으면 '없으면' 블록이나 '키가 있는가'를 쓴다.
Blockly.Blocks["dict_get"] = {
  init: function () {
    this.jsonInit({
      message0: "%1 에서 키 %2 의 값",
      args0: [
        { type: "input_value", name: "DICT", check: "Dict" },
        { type: "input_value", name: "KEY" },
      ],
      inputsInline: true,
      output: null,
      style: "variable_blocks",
      tooltip: "딕셔너리에서 키에 짝지어진 값을 가져옵니다. 키가 없으면 오류가 납니다. '설정' 블록 앞 칸에 넣으면 값을 넣거나 바꿉니다.",
      helpUrl: "",
    });
  },
};
pythonGenerator.forBlock["dict_get"] = function (block, generator) {
  const dict = generator.valueToCode(block, "DICT", Order.MEMBER) || "{}";
  const key = generator.valueToCode(block, "KEY", Order.NONE) || "''";
  return [`${dict}[${key}]`, Order.MEMBER];
};

// [d] 에서 키 [k] 의 값 (없으면 [0]) → d.get(k, 0)
Blockly.Blocks["dict_get_default"] = {
  init: function () {
    this.jsonInit({
      message0: "%1 에서 키 %2 의 값 (없으면 %3 )",
      args0: [
        { type: "input_value", name: "DICT", check: "Dict" },
        { type: "input_value", name: "KEY" },
        { type: "input_value", name: "DEFAULT" },
      ],
      inputsInline: true,
      output: null,
      style: "variable_blocks",
      tooltip: "딕셔너리에서 키의 값을 가져옵니다. 키가 없으면 오류 대신 뒤 칸의 값을 씁니다.",
      helpUrl: "",
    });
  },
};
pythonGenerator.forBlock["dict_get_default"] = function (block, generator) {
  const dict = generator.valueToCode(block, "DICT", Order.MEMBER) || "{}";
  const key = generator.valueToCode(block, "KEY", Order.NONE) || "''";
  const fallback = generator.valueToCode(block, "DEFAULT", Order.NONE) || "0";
  return [`${dict}.get(${key}, ${fallback})`, Order.FUNCTION_CALL];
};

// [d] 에 키 [k] 이(가) 있는가 → k in d
Blockly.Blocks["dict_has_key"] = {
  init: function () {
    this.jsonInit({
      message0: "%1 에 키 %2 이(가) 있는가",
      args0: [
        { type: "input_value", name: "DICT", check: "Dict" },
        { type: "input_value", name: "KEY" },
      ],
      inputsInline: true,
      output: "Boolean",
      style: "logic_blocks",
      tooltip: "딕셔너리에 그 키가 있으면 참, 없으면 거짓입니다.",
      helpUrl: "",
    });
  },
};
pythonGenerator.forBlock["dict_has_key"] = function (block, generator) {
  const dict = generator.valueToCode(block, "DICT", Order.RELATIONAL) || "{}";
  const key = generator.valueToCode(block, "KEY", Order.RELATIONAL) || "''";
  return [`${key} in ${dict}`, Order.RELATIONAL];
};

// [d] 의 키 목록 → list(d)  ('요소로 반복'에 넣어 키마다 반복한다)
Blockly.Blocks["dict_keys"] = {
  init: function () {
    this.jsonInit({
      message0: "%1 의 키 목록",
      args0: [{ type: "input_value", name: "DICT", check: "Dict" }],
      inputsInline: true,
      output: "Array",
      style: "list_blocks",
      tooltip: "딕셔너리의 키들을 넣은 순서대로 리스트로 만듭니다.",
      helpUrl: "",
    });
  },
};
pythonGenerator.forBlock["dict_keys"] = function (block, generator) {
  const dict = generator.valueToCode(block, "DICT", Order.NONE) || "{}";
  return [`list(${dict})`, Order.FUNCTION_CALL];
};
