// 수학 카테고리 Toolbox 설정
export const mathCategory = {
  kind: "category",
  name: "수학",
  categorystyle: "math_category",
  contents: [
    {
      type: "math_number",
      kind: "block",
      fields: {
        NUM: 123,
      },
    },

    // 텍스트를 숫자로 변환
    {
      kind: "block",
      type: "text_to_number",
      inputs: {
        TXT: {
          shadow: {
            type: "text",
            fields: { TEXT: "10" },
          },
        },
      },
    },

    // 사칙연산
    {
      kind: "block",
      type: "calc_basic",
      inputs: {
        A: { shadow: { type: "math_number", fields: { NUM: 1 } } },
        B: { shadow: { type: "math_number", fields: { NUM: 1 } } },
      },
    },

    // 나눗기(몫, 나머지)
    {
      kind: "block",
      type: "calc_division",
      inputs: {
        A: { shadow: { type: "math_number", fields: { NUM: 10 } } },
        B: { shadow: { type: "math_number", fields: { NUM: 3 } } },
      },
    },

    // 리스트 통계 (합/최소값/최대값)
    {
      kind: "block",
      type: "list_stats",
      inputs: {
        LIST: {
          shadow: { type: "lists_create_with", extraState: { itemCount: 0 } },
        },
      },
    },
  ],
};
