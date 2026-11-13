// 딕셔너리 카테고리 Toolbox 설정
// 키로 값을 찾는 자료(다른 언어의 맵). 블록 이름은 학생이 코드 보기·오류에서 만나는
// 파이썬 이름(딕셔너리)으로 하고, 메뉴에만 일반 이름(맵)을 함께 적는다.
// 값을 넣고 바꿀 때는 '설정'·'바꾸기' 앞 칸에 '키의 값' 블록을 끼운다(따로 블록 없음).
export const dictCategory = {
  kind: "category",
  name: "딕셔너리(맵)",
  categorystyle: "list_category",
  contents: [
    { kind: "block", type: "dict_create_empty" },
    {
      kind: "block",
      type: "dict_get",
      inputs: {
        DICT: { shadow: { type: "dict_create_empty" } },
        KEY: { shadow: { type: "text", fields: { TEXT: "" } } },
      },
    },
    {
      kind: "block",
      type: "dict_get_default",
      inputs: {
        DICT: { shadow: { type: "dict_create_empty" } },
        KEY: { shadow: { type: "text", fields: { TEXT: "" } } },
        DEFAULT: { shadow: { type: "math_number", fields: { NUM: 0 } } },
      },
    },
    {
      kind: "block",
      type: "dict_has_key",
      inputs: {
        DICT: { shadow: { type: "dict_create_empty" } },
        KEY: { shadow: { type: "text", fields: { TEXT: "" } } },
      },
    },
    {
      kind: "block",
      type: "dict_keys",
      inputs: { DICT: { shadow: { type: "dict_create_empty" } } },
    },
  ],
};
