// 입출력 카테고리 Toolbox 설정
export const ioCategory = {
  kind: "category",
  name: "입출력",
  colour: "#4185F4",
  contents: [
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
  ],
};
