// 리스트 카테고리 Toolbox 설정
export const listCategory = {
  kind: "category",
  name: "리스트",
  categorystyle: "list_category",
  contents: [
    { kind: "block", type: "lists_create_with" },
    {
      kind: "block",
      type: "lists_repeat",
      inputs: { NUM: { shadow: { type: "math_number", fields: { NUM: 5 } } } },
    },

    // 텍스트를 분리하기
    {
      kind: "block",
      type: "text_split",
      inputs: {
        TXT: { shadow: { type: "text" } },
        SEP: { shadow: { type: "text" } },
      },
    },

    // 리스트 값을 모두 숫자로 바꾸기
    {
      kind: "block",
      type: "list_map_number",
      inputs: {
        LIST: {
          shadow: { type: "lists_create_with", extraState: { itemCount: 0 } },
        },
      },
    },

    {
      kind: "block",
      type: "lists_length",
      inputs: {
        VALUE: {
          shadow: { type: "lists_create_with", extraState: { itemCount: 0 } },
        },
      },
    },

    // 리스트 인덱싱
    {
      kind: "block",
      type: "list_get_nth",
      inputs: {
        LIST: {
          shadow: {
            type: "lists_create_with",
            extraState: { itemCount: 0 },
          },
        },
        INDEX: { shadow: { type: "math_number", fields: { NUM: 0 } } },
      },
    },

    // 리스트 값 추가하기
    {
      kind: "block",
      type: "list_append",
      inputs: {
        LIST: {
          shadow: { type: "lists_create_with", extraState: { itemCount: 0 } },
        },
      },
    },

    // 리스트 값 삭제하기
    {
      kind: "block",
      type: "list_pop",
      inputs: {
        LIST: {
          shadow: { type: "lists_create_with", extraState: { itemCount: 0 } },
        },
      },
    },

    // 리스트 정렬하기
    {
      kind: "block",
      type: "list_sort",
      inputs: {
        LIST: {
          shadow: { type: "lists_create_with", extraState: { itemCount: 0 } },
        },
      },
    },

    // { kind: "block", type: "lists_isEmpty" },
    //     {
    //       kind: "block",
    //       type: "lists_indexOf",
    //       fields: { END: "FIRST" },
    //       inputs: {
    //         VALUE: {
    //           block: { type: "variables_get", fields: { VAR: { name: "list" } } },
    //         },
    //       },
    //     },
    //     {
    //       kind: "block",
    //       type: "lists_getIndex",
    //       fields: { MODE: "GET", WHERE: "FROM_START" },
    //       inputs: {
    //         VALUE: {
    //           block: { type: "variables_get", fields: { VAR: { name: "list" } } },
    //         },
    //       },
    //     },
    //     {
    //       kind: "block",
    //       type: "lists_setIndex",
    //       fields: { MODE: "SET", WHERE: "FROM_START" },
    //       inputs: {
    //         LIST: {
    //           block: { type: "variables_get", fields: { VAR: { name: "list" } } },
    //         },
    //       },
    //     },
    //     {
    //       kind: "block",
    //       type: "lists_getSublist",
    //       fields: { WHERE1: "FROM_START", WHERE2: "FROM_START" },
    //       inputs: {
    //         LIST: {
    //           block: { type: "variables_get", fields: { VAR: { name: "list" } } },
    //         },
    //       },
    //     },
    //     {
    //       kind: "block",
    //       type: "lists_split",
    //       fields: { MODE: "SPLIT" },
    //       inputs: { DELIM: { shadow: { type: "text", fields: { TEXT: "," } } } },
    //     },
    //     {
    //       kind: "block",
    //       type: "lists_sort",
    //       fields: { TYPE: "NUMERIC", DIRECTION: "1" },
    //     },
    //     { type: "lists_reverse", kind: "block" },
  ],
};
