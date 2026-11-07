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
];

// 입출력 블록 뒤에 Blockly 기본 변수 목록('변수 만들기' 버튼 포함)을 붙인다
export function ioVariableFlyout(workspace) {
  return [...ioBlocks, ...Blockly.Variables.flyoutCategory(workspace, false)];
}
