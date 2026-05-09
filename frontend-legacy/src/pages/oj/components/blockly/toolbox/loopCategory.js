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
    {
      type: "controls_whileUntil",
      kind: "block",
      fields: { MODE: "WHILE" },
    },
    // {
    //   type: "controls_for",
    //   kind: "block",
    //   fields: { VAR: { name: "i" } },
    //   inputs: {
    //     FROM: { shadow: { type: "math_number", fields: { NUM: 1 } } },
    //     TO: { shadow: { type: "math_number", fields: { NUM: 10 } } },
    //     BY: { shadow: { type: "math_number", fields: { NUM: 1 } } },
    //   },
    // },
    // {
    //   type: "controls_forEach",
    //   kind: "block",
    //   fields: {
    //     VAR: {
    //       name: "j",
    //     },
    //   },
    // },
    {
      type: "controls_flow_statements",
      kind: "block",
      fields: {
        FLOW: "BREAK",
      },
    },
  ],
};
