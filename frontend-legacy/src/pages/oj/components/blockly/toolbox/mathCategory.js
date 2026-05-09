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

    //     {
    //       type: "math_single",
    //       kind: "block",
    //       fields: {
    //         OP: "ROOT",
    //       },
    //       inputs: {
    //         NUM: {
    //           shadow: {
    //             type: "math_number",
    //             fields: {
    //               NUM: 9,
    //             },
    //           },
    //         },
    //       },
    //     },
    //     {
    //       type: "math_trig",
    //       kind: "block",
    //       fields: {
    //         OP: "SIN",
    //       },
    //       inputs: {
    //         NUM: {
    //           shadow: {
    //             type: "math_number",
    //             fields: {
    //               NUM: 45,
    //             },
    //           },
    //         },
    //       },
    //     },
    //     {
    //       type: "math_constant",
    //       kind: "block",
    //       fields: {
    //         CONSTANT: "PI",
    //       },
    //     },
    //     {
    //       type: "math_number_property",
    //       kind: "block",
    //       fields: {
    //         PROPERTY: "EVEN",
    //       },
    //       inputs: {
    //         NUMBER_TO_CHECK: {
    //           shadow: {
    //             type: "math_number",
    //             fields: {
    //               NUM: 0,
    //             },
    //           },
    //         },
    //       },
    //     },
    //     {
    //       type: "math_round",
    //       kind: "block",
    //       fields: {
    //         OP: "ROUND",
    //       },
    //       inputs: {
    //         NUM: {
    //           shadow: {
    //             type: "math_number",
    //             fields: {
    //               NUM: 3.1,
    //             },
    //           },
    //         },
    //       },
    //     },
    //     {
    //       type: "math_on_list",
    //       kind: "block",
    //       fields: {
    //         OP: "SUM",
    //       },
    //     },
    //     {
    //       type: "math_modulo",
    //       kind: "block",
    //       inputs: {
    //         DIVIDEND: {
    //           shadow: {
    //             type: "math_number",
    //             fields: {
    //               NUM: 64,
    //             },
    //           },
    //         },
    //         DIVISOR: {
    //           shadow: {
    //             type: "math_number",
    //             fields: {
    //               NUM: 10,
    //             },
    //           },
    //         },
    //       },
    //     },
    //     {
    //       type: "math_constrain",
    //       kind: "block",
    //       inputs: {
    //         VALUE: {
    //           shadow: {
    //             type: "math_number",
    //             fields: {
    //               NUM: 50,
    //             },
    //           },
    //         },
    //         LOW: {
    //           shadow: {
    //             type: "math_number",
    //             fields: {
    //               NUM: 1,
    //             },
    //           },
    //         },
    //         HIGH: {
    //           shadow: {
    //             type: "math_number",
    //             fields: {
    //               NUM: 100,
    //             },
    //           },
    //         },
    //       },
    //     },
    //     {
    //       type: "math_random_int",
    //       kind: "block",
    //       inputs: {
    //         FROM: {
    //           shadow: {
    //             type: "math_number",
    //             fields: {
    //               NUM: 1,
    //             },
    //           },
    //         },
    //         TO: {
    //           shadow: {
    //             type: "math_number",
    //             fields: {
    //               NUM: 100,
    //             },
    //           },
    //         },
    //       },
    //     },
    //     {
    //       type: "math_random_float",
    //       kind: "block",
    //     },
    //     {
    //       type: "math_atan2",
    //       kind: "block",
    //       inputs: {
    //         X: {
    //           shadow: {
    //             type: "math_number",
    //             fields: {
    //               NUM: 1,
    //             },
    //           },
    //         },
    //         Y: {
    //           shadow: {
    //             type: "math_number",
    //             fields: {
    //               NUM: 1,
    //             },
    //           },
    //         },
    //       },
    //     },
  ],
};
