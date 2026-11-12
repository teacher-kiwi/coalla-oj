import * as Blockly from "blockly";
import "blockly/blocks"; // 기본 함수 블록을 먼저 등록해야 아래에서 빌려 쓸 수 있다
import { pythonGenerator, Order } from "blockly/python";
import { setDisabledQuietly } from "./variableBlocks";

// 함수 카테고리 커스텀 블록
//
// 함수 만들기 블록은 하나(procedures_defnoreturn)만 두고, 값을 돌려줄 때는 '돌려줌' 블록을
// 함수 안 아무 데나(만약 블록 안 포함) 넣는다. 파이썬의 def + return 과 같은 모양이다.
// (돌려주는 함수·만약~돌려줌 기본 블록은 이미 저장된 블록이 열리도록 등록은 그대로 둔다)

const FUNCTION_TYPES = ["procedures_defnoreturn", "procedures_defreturn"];
const OUTSIDE_FUNCTION = "RETURN_OUTSIDE_FUNCTION";

function insideFunction(block) {
  for (let b = block.getSurroundParent(); b; b = b.getSurroundParent()) {
    if (FUNCTION_TYPES.includes(b.type)) return true;
  }
  return false;
}

// [값] 을(를) 돌려줌 → return 값 (값 칸이 비면 return)
Blockly.Blocks["procedure_return"] = {
  init: function () {
    this.jsonInit({
      message0: "%1 을(를) 돌려줌",
      args0: [{ type: "input_value", name: "VALUE" }],
      inputsInline: true,
      previousStatement: null,
      style: "procedure_blocks",
      tooltip: "함수를 끝내고 값을 돌려줍니다. 값 칸을 비우면 돌려주는 값 없이 끝냅니다.",
      helpUrl: "",
    });
  },
  // 함수 밖의 return 은 파이썬 전체를 문법 오류로 멈추게 하므로 끈다
  onchange: function () {
    if (!this.workspace || this.isInFlyout || this.isDeadOrDying()) return;
    const ok = insideFunction(this);
    if (this.hasDisabledReason(OUTSIDE_FUNCTION) === !ok) return;
    this.setWarningText(ok ? null : "이 블록은 함수 안에서만 쓸 수 있어요.");
    setDisabledQuietly(this, !ok, OUTSIDE_FUNCTION);
  },
};
pythonGenerator.forBlock["procedure_return"] = function (block, generator) {
  const value = generator.valueToCode(block, "VALUE", Order.NONE);
  return value ? `return ${value}\n` : "return\n";
};

// 함수를 값으로 쓰는 블록: res = 가위바위보(i)
// Blockly 기본 값 블록(procedures_callreturn)은 '돌려주는 함수' 블록과만 짝이 된다.
// 함수 만들기 블록과 짝이 맞지 않으면 꺼낼 때 같은 이름의 함수를 하나 더 만들어 버리므로,
// 짝을 함수 만들기 블록으로 바꾼 값 블록을 따로 둔다. 나머지 동작은 기본과 같다.
Blockly.Blocks["procedure_call_value"] = {
  ...Blockly.Blocks["procedures_callreturn"],
  defType_: "procedures_defnoreturn",
};
pythonGenerator.forBlock["procedure_call_value"] = function (block, generator) {
  return pythonGenerator.forBlock["procedures_callreturn"].call(this, block, generator);
};
