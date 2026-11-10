// 반복 카테고리 Toolbox 설정
export const loopCategory = {
  kind: "category",
  name: "반복",
  categorystyle: "loop_category",
  contents: [
    {
      type: "controls_repeat_ext",
      kind: "block",
      inputs: {
        TIMES: { shadow: { type: "math_number", fields: { NUM: 10 } } },
      },
    },
    // 범위 반복 (for i in range(시작, 끝))
    {
      type: "loop_range",
      kind: "block",
      inputs: {
        FROM: { shadow: { type: "math_number", fields: { NUM: 0 } } },
        TO: { shadow: { type: "math_number", fields: { NUM: 10 } } },
      },
    },
    // 각 요소 반복 (for 값 in 리스트)
    {
      type: "loop_each",
      kind: "block",
      inputs: {
        LIST: { shadow: { type: "lists_create_with", extraState: { itemCount: 0 } } },
      },
    },
    {
      type: "controls_whileUntil",
      kind: "block",
      fields: { MODE: "WHILE" },
    },
    {
      type: "controls_flow_statements",
      kind: "block",
      fields: {
        FLOW: "BREAK",
      },
    },
  ],
};
