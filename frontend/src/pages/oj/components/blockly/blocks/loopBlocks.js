import * as Blockly from "blockly";
import { loops } from "blockly/blocks";
import { pythonGenerator, Order } from "blockly/python";

// 반복 카테고리 커스텀 블록
//
// 반복 변수(i, 값)는 블록 안의 글자 칸에 학생이 직접 이름을 쓴다.
// Blockly 기본 블록처럼 변수 고르기 칸을 쓰지 않는 이유: "새 변수 [i]" 처럼
// 이름을 쓰는 것이 파이썬의 for i in ... 와 더 가깝고 처음 보는 학생도 바로 안다.
// 그 이름은 '입출력/변수' 칸에 변수로 자동으로 생겨, 반복 안에서 꺼내 쓸 수 있다.

const VAR_FIELD = "VAR";

// 비우거나 공백만 쓰면 받지 않고 앞 이름으로 되돌린다. 빈 이름은 파이썬 문법 오류다.
function validateName(text) {
  const name = (text || "").trim();
  return name || null;
}

// 이름 칸의 이름을 작업 공간 변수로 만든다. 이미 있으면 그 변수를 같이 쓴다.
function ensureVariable(block) {
  const workspace = block.workspace;
  if (!workspace || workspace.isFlyout || block.isDeadOrDying()) return;
  const name = block.getFieldValue(VAR_FIELD);
  const variables = workspace.getVariableMap();
  if (name && !variables.getVariable(name)) variables.createVariable(name);
}

// 두 반복 블록이 함께 쓰는 변경 처리.
// 글자를 칠 때마다가 아니라, 블록이 생기거나 이름 입력을 마쳤을 때만 변수를 만든다
// (칠 때마다 만들면 'ㄱ', '가', '값' 이 모두 변수로 남는다).
function onLoopChange(event) {
  if (!this.workspace || this.workspace.isFlyout) return;
  const E = Blockly.Events;
  if (event.type === E.BLOCK_CREATE && (event.ids || []).includes(this.id)) {
    ensureVariable(this);
  } else if (event.type === E.BLOCK_CHANGE && event.blockId === this.id && event.name === VAR_FIELD) {
    ensureVariable(this);
  } else if (event.type === E.VAR_RENAME && event.oldName === this.getFieldValue(VAR_FIELD)) {
    // 변수 고르기 칸에서 이름을 바꾸면 반복 블록의 이름도 따라 바꾼다.
    // 안 그러면 반복은 옛 이름으로, 안쪽 블록은 새 이름으로 갈라진다.
    this.setFieldValue(event.newName, VAR_FIELD);
  }
}

function loopVariable(block, generator) {
  // 이름으로 찾아도 변수 칸의 블록(variables_get)과 같은 파이썬 이름이 나온다
  return generator.getVariableName(block.getFieldValue(VAR_FIELD));
}

function loopBody(block, generator) {
  const branch = generator.statementToCode(block, "DO");
  return generator.addLoopTrap(branch, block) || generator.PASS;
}

// 범위 반복: for i in range(시작, 끝)
// 끝값은 넣지 않는다(파이썬 range 와 같다). 간격은 두지 않는다(수업 결정).
Blockly.Blocks["loop_range"] = {
  init: function () {
    this.jsonInit({
      message0: "새 변수 %1 을(를) %2 부터 %3 전까지 반복",
      args0: [
        { type: "field_input", name: VAR_FIELD, text: "i" },
        { type: "input_value", name: "FROM", check: "Number" },
        { type: "input_value", name: "TO", check: "Number" },
      ],
      message1: "%1",
      args1: [{ type: "input_statement", name: "DO" }],
      inputsInline: true,
      previousStatement: null,
      nextStatement: null,
      style: "loop_blocks",
      tooltip: "변수가 시작 값부터 끝 값 바로 앞까지 1씩 커지며 반복합니다. 끝 값은 포함하지 않습니다.",
      helpUrl: "",
    });
    this.getField(VAR_FIELD).setValidator(validateName);
  },
  onchange: onLoopChange,
};
pythonGenerator.forBlock["loop_range"] = function (block, generator) {
  const variable = loopVariable(block, generator);
  const from = generator.valueToCode(block, "FROM", Order.NONE) || "0";
  const to = generator.valueToCode(block, "TO", Order.NONE) || "0";
  return `for ${variable} in range(${from}, ${to}):\n${loopBody(block, generator)}`;
};

// 각 요소 반복: for 값 in 리스트 (텍스트를 넣으면 한 글자씩: for 글자 in a)
Blockly.Blocks["loop_each"] = {
  init: function () {
    this.jsonInit({
      message0: "새 변수 %1 을(를) 리스트 %2 의 요소로 반복",
      args0: [
        { type: "field_input", name: VAR_FIELD, text: "값" },
        { type: "input_value", name: "LIST", check: ["Array", "String"] },
      ],
      message1: "%1",
      args1: [{ type: "input_statement", name: "DO" }],
      inputsInline: true,
      previousStatement: null,
      nextStatement: null,
      style: "loop_blocks",
      tooltip: "리스트의 값을 앞에서부터 하나씩 변수에 넣으며 반복합니다. 텍스트를 넣으면 한 글자씩 넣습니다.",
      helpUrl: "",
    });
    this.getField(VAR_FIELD).setValidator(validateName);
  },
  onchange: onLoopChange,
};
pythonGenerator.forBlock["loop_each"] = function (block, generator) {
  const variable = loopVariable(block, generator);
  const list = generator.valueToCode(block, "LIST", Order.RELATIONAL) || "[]";
  return `for ${variable} in ${list}:\n${loopBody(block, generator)}`;
};

// '반복 멈추기·다음 반복으로' 블록은 Blockly 가 아는 반복 블록 안에서만 켜진다.
// 등록하지 않으면 이 블록들 안에 넣어도 "반복 안에서만 쓸 수 있다" 며 꺼진다.
loops.loopTypes.add("loop_range");
loops.loopTypes.add("loop_each");
