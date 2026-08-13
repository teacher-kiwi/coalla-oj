// 텍스트 카테고리 Toolbox 설정
export const textCategory = {
  kind: "category",
  name: "텍스트",
  categorystyle: "text_category",
  contents: [
    { type: "text", kind: "block", fields: { TEXT: "" } },
    { type: "text_join", kind: "block" },

    {
      kind: "block",
      type: "text_length",
      inputs: { VALUE: { shadow: { type: "text", fields: { TEXT: "" } } } },
    },

    // 텍스트 인덱싱
    {
      kind: "block",
      type: "text_get_nth",
      inputs: {
        TXT: {
          shadow: {
            type: "text",
            fields: { TEXT: "" },
          },
        },
        INDEX: { shadow: { type: "math_number", fields: { NUM: 0 } } },
      },
    },
  ],
};
