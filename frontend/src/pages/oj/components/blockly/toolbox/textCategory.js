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

    // {
    //   kind: "block",
    //   type: "text_append",
    //   fields: { VAR: "item" },
    //   inputs: { TEXT: { shadow: { type: "text", fields: { TEXT: "" } } } },
    // },
    // {
    //   kind: "block",
    //   type: "text_isEmpty",
    //   inputs: { VALUE: { shadow: { type: "text", fields: { TEXT: "" } } } },
    // },
    // {
    //   kind: "block",
    //   type: "text_indexOf",
    //   fields: { END: "FIRST" },
    //   inputs: {
    //     VALUE: {
    //       block: { type: "variables_get", fields: { VAR: { name: "text" } } },
    //     },
    //     FIND: { shadow: { type: "text", fields: { TEXT: "abc" } } },
    //   },
    // },
    // {
    //   kind: "block",
    //   type: "text_charAt",
    //   fields: { WHERE: "FROM_START" },
    //   inputs: {
    //     VALUE: {
    //       block: { type: "variables_get", fields: { VAR: { name: "text" } } },
    //     },
    //   },
    // },
    // {
    //   kind: "block",
    //   type: "text_getSubstring",
    //   fields: { WHERE1: "FROM_START", WHERE2: "FROM_START" },
    //   inputs: {
    //     STRING: {
    //       block: { type: "variables_get", fields: { VAR: { name: "text" } } },
    //     },
    //   },
    // },
    // {
    //   type: "text_changeCase",
    //   kind: "block",
    //   fields: { CASE: "UPPERCASE" },
    //   inputs: { TEXT: { shadow: { type: "text", fields: { TEXT: "abc" } } } },
    // },
    // {
    //   type: "text_trim",
    //   kind: "block",
    //   fields: { MODE: "BOTH" },
    //   inputs: { TEXT: { shadow: { type: "text", fields: { TEXT: "abc" } } } },
    // },
    // {
    //   type: "text_count",
    //   kind: "block",
    //   inputs: {
    //     SUB: { shadow: { type: "text", fields: { TEXT: "" } } },
    //     TEXT: { shadow: { type: "text", fields: { TEXT: "" } } },
    //   },
    // },
    // {
    //   type: "text_replace",
    //   kind: "block",
    //   inputs: {
    //     FROM: { shadow: { type: "text", fields: { TEXT: "" } } },
    //     TO: { shadow: { type: "text", fields: { TEXT: "" } } },
    //     TEXT: { shadow: { type: "text", fields: { TEXT: "" } } },
    //   },
    // },
    // {
    //   type: "text_reverse",
    //   kind: "block",
    //   inputs: { TEXT: { shadow: { type: "text", fields: { TEXT: "" } } } },
    // },
    // {
    //   type: "text_prompt_ext",
    //   kind: "block",
    //   fields: { TYPE: "TEXT" },
    //   inputs: { TEXT: { shadow: { type: "text", fields: { TEXT: "abc" } } } },
    // },
  ],
};
