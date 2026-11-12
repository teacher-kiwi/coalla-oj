import * as Blockly from "blockly";

// 입출력/변수 카테고리 Toolbox 설정
// 입력받은 값을 변수에 넣는 일이 대부분이라 한 곳에 모았다.
// 변수 블록은 학생이 만든 변수에 따라 달라지므로 Blockly 가 그때그때 그린다
// (custom). 그 앞에 입출력 블록을 붙이는 것은 ioVariableFlyout 이 한다.
export const IO_VARIABLE_CATEGORY = "IO_VARIABLE";

export const ioCategory = {
  kind: "category",
  name: "입출력/변수",
  colour: "#4185F4",
  custom: IO_VARIABLE_CATEGORY,
};

const ioBlocks = [
  // 텍스트로 한 줄 입력
  {
    kind: "block",
    type: "input_readline",
  },

  {
    kind: "block",
    type: "text_print",
    inputs: {
      TEXT: {
        shadow: {
          type: "text",
          fields: { TEXT: "Hello" },
        },
      },
    },
  },

  // 리스트를 띄어서 출력 (print(*리스트))
  {
    kind: "block",
    type: "print_list_spaced",
    inputs: {
      LIST: { shadow: { type: "lists_create_with", extraState: { itemCount: 0 } } },
    },
  },
];

// 변수 블록 목록. Blockly 기본 목록과 같지만 '설정'·'바꾸기'를 앞 칸이 뚫린 우리 블록으로 바꿨다.
// 앞 칸에는 가장 최근에 만든 변수 블록을 끼워 두어, 지금처럼 바로 쓰거나 빼고 리스트 값을 넣는다.
export function variableFlyoutBlocks(workspace) {
  const variables = workspace.getVariableMap().getVariablesOfType("");
  if (!variables.length) return [];
  const varBlock = (v) => ({
    type: "variables_get",
    fields: { VAR: { name: v.getName(), type: v.getType() } },
  });
  const latest = variables[variables.length - 1];
  const sorted = [...variables].sort(Blockly.Variables.compareByName);
  return [
    { kind: "block", type: "variable_assign", gap: 8, inputs: { TARGET: { block: varBlock(latest) } } },
    {
      kind: "block",
      type: "variable_change",
      gap: 20,
      inputs: {
        TARGET: { block: varBlock(latest) },
        DELTA: { shadow: { type: "math_number", fields: { NUM: 1 } } },
      },
    },
    ...sorted.map((v) => ({ kind: "block", gap: 8, ...varBlock(v) })),
  ];
}

// 입출력 블록 + '변수 만들기' 버튼 + 변수 블록
export function ioVariableFlyout(workspace) {
  workspace.registerButtonCallback("CREATE_VARIABLE", (button) => {
    Blockly.Variables.createVariableButtonHandler(button.getTargetWorkspace());
  });
  return [
    ...ioBlocks,
    { kind: "button", text: "%{BKY_NEW_VARIABLE}", callbackkey: "CREATE_VARIABLE" },
    ...variableFlyoutBlocks(workspace),
  ];
}
