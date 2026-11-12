import * as Blockly from "blockly";
import { pythonGenerator, Order } from "blockly/python";

// 변수 카테고리 커스텀 블록
//
// Blockly 기본 '설정'·'바꾸기' 블록은 앞이 변수 고르기 칸이라 리스트 값(a[i])을 바꿀 수 없다.
// 그래서 앞을 값 칸으로 뚫어, 변수 블록이나 리스트의 n번 값 블록을 끼우게 했다.
// 도구 상자에서는 변수 블록이 미리 끼워진 채로 나와서 지금처럼 바로 쓸 수 있다.
// (기본 블록은 이미 저장된 블록이 열리도록 등록은 그대로 둔다)

// 앞 칸에 넣을 수 있는 블록. 파이썬에서 '= 의 왼쪽'에 올 수 있는 것만 받는다.
// 숫자·계산식은 문법 오류, 글자(문자열의 n번 글자)는 바꿀 수 없어 실행 오류가 난다.
export const ASSIGNABLE_TYPES = new Set(["variables_get", "list_get_nth"]);

const NOT_ASSIGNABLE = "NOT_ASSIGNABLE";
const NOT_ASSIGNABLE_WARNING = "앞 칸에는 변수나 리스트의 값만 넣을 수 있어요.";

// 앞 칸이 비었거나 바꿀 수 없는 블록이면 블록을 끄고 이유를 보여 준다.
// 꺼진 블록은 코드에서 빠지므로, 고칠 때까지 프로그램 전체가 문법 오류로 멈추지 않는다.
function checkTarget() {
  if (!this.workspace || this.isInFlyout || this.isDeadOrDying()) return;
  const target = this.getInputTargetBlock("TARGET");
  const ok = !!target && ASSIGNABLE_TYPES.has(target.type);
  if (this.hasDisabledReason(NOT_ASSIGNABLE) === !ok) return;
  this.setWarningText(ok ? null : NOT_ASSIGNABLE_WARNING);
  setDisabledQuietly(this, !ok, NOT_ASSIGNABLE);
}

// 끄고 켜는 것은 학생이 한 일이 아니라서 되돌리기 기록에 남기지 않는다(Blockly 기본 블록과 같음)
export function setDisabledQuietly(block, disabled, reason) {
  Blockly.Events.setRecordUndo(false);
  try {
    block.setDisabledReason(disabled, reason);
  } finally {
    Blockly.Events.setRecordUndo(true);
  }
}

function targetCode(block, generator) {
  return generator.valueToCode(block, "TARGET", Order.NONE);
}

// [변수] 을(를) [값] (으)로 설정 → 변수 = 값 / 리스트[번호] = 값
Blockly.Blocks["variable_assign"] = {
  init: function () {
    this.jsonInit({
      message0: "%1 을(를) %2 (으)로 설정",
      args0: [
        { type: "input_value", name: "TARGET" },
        { type: "input_value", name: "VALUE" },
      ],
      inputsInline: true,
      previousStatement: null,
      nextStatement: null,
      style: "variable_blocks",
      tooltip: "앞 칸의 변수(또는 리스트의 값)에 뒤 칸의 값을 넣습니다.",
      helpUrl: "",
    });
  },
  onchange: checkTarget,
};
pythonGenerator.forBlock["variable_assign"] = function (block, generator) {
  const target = targetCode(block, generator);
  if (!target) return "";
  const value = generator.valueToCode(block, "VALUE", Order.NONE) || "0";
  return `${target} = ${value}\n`;
};

// [변수] 을(를) [1] 만큼 바꾸기 → 변수 += 1
Blockly.Blocks["variable_change"] = {
  init: function () {
    this.jsonInit({
      message0: "%1 을(를) %2 만큼 바꾸기",
      args0: [
        { type: "input_value", name: "TARGET" },
        { type: "input_value", name: "DELTA", check: "Number" },
      ],
      inputsInline: true,
      previousStatement: null,
      nextStatement: null,
      style: "variable_blocks",
      tooltip: "앞 칸의 변수(또는 리스트의 값)에 뒤 칸의 수를 더합니다. 빼려면 음수를 넣습니다.",
      helpUrl: "",
    });
  },
  onchange: checkTarget,
};
pythonGenerator.forBlock["variable_change"] = function (block, generator) {
  const target = targetCode(block, generator);
  if (!target) return "";
  const delta = generator.valueToCode(block, "DELTA", Order.NONE) || "0";
  return `${target} += ${delta}\n`;
};

// 예전 '바꾸기' 블록(저장된 블록)도 같은 한 줄로 만든다.
// Blockly 기본은 (x if isinstance(x, Number) else 0) + 1 과 import 를 붙여, 코드 보기에서 학생이 헷갈린다.
pythonGenerator.forBlock["math_change"] = function (block, generator) {
  const name = generator.getVariableName(block.getFieldValue("VAR"));
  const delta = generator.valueToCode(block, "DELTA", Order.NONE) || "0";
  return `${name} += ${delta}\n`;
};
