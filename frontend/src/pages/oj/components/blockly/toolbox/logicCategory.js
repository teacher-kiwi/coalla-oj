// 논리 카테고리 Toolbox 설정
export const logicCategory = {
  kind: "category",
  name: "논리",
  categorystyle: "logic_category",
  contents: [
    { kind: "block", type: "controls_if" },
    { kind: "block", type: "logic_boolean", fields: { BOOL: "TRUE" } },
    { type: "logic_compare", kind: "block", fields: { OP: "EQ" } },
    {
      type: "logic_operation",
      kind: "block",
      fields: {
        OP: "AND",
      },
    },
    {
      type: "logic_negate",
      kind: "block",
    },
    // {
    //   type: "logic_null",
    //   kind: "block",
    // },
    // {
    //   type: "logic_ternary",
    //   kind: "block",
    // },
  ],
};
