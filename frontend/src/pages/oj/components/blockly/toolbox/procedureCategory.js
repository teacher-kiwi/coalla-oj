import * as Blockly from "blockly";

// 함수 카테고리 Toolbox 설정
// 함수 블록은 학생이 만든 함수에 따라 달라지므로 그때그때 그린다(custom).
// Blockly 기본 함수 칸 대신 우리 목록을 쓴다:
//  - 함수 만들기 블록은 하나만, 값을 돌려줄 때는 '돌려줌' 블록을 안에 넣는다
//  - 함수마다 '실행(한 줄)' 블록과 '값' 블록을 둘 다 꺼내 준다
export const PROCEDURE_CATEGORY = "COALLA_PROCEDURE";

export const procedureCategory = {
  kind: "category",
  name: "함수",
  categorystyle: "procedure_category",
  custom: PROCEDURE_CATEGORY,
};

export function procedureFlyout(workspace) {
  const items = [
    {
      kind: "block",
      type: "procedures_defnoreturn",
      gap: 16,
      fields: { NAME: Blockly.Msg["PROCEDURES_DEFNORETURN_PROCEDURE"] },
    },
    { kind: "block", type: "procedure_return", gap: 24 },
  ];
  // [0] 함수 만들기 블록으로 만든 함수, [1] 예전 '돌려주는 함수' 블록으로 만든 함수
  const [plain, legacy] = Blockly.Procedures.allProcedures(workspace);
  for (const [name, params] of plain) {
    const extraState = { name, params };
    items.push({ kind: "block", type: "procedures_callnoreturn", gap: 8, extraState });
    items.push({ kind: "block", type: "procedure_call_value", gap: 16, extraState });
  }
  for (const [name, params] of legacy) {
    items.push({ kind: "block", type: "procedures_callreturn", gap: 16, extraState: { name, params } });
  }
  return items;
}
