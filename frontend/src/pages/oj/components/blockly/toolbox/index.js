import { ioCategory } from "./ioCategory";
import { logicCategory } from "./logicCategory";
import { loopCategory } from "./loopCategory";
import { mathCategory } from "./mathCategory";
import { textCategory } from "./textCategory";
import { listCategory } from "./listCategory";
import { procedureCategory } from "./procedureCategory";

export { IO_VARIABLE_CATEGORY, ioVariableFlyout } from "./ioCategory";
export { PROCEDURE_CATEGORY, procedureFlyout } from "./procedureCategory";

export const toolboxConfig = {
  kind: "categoryToolbox",
  contents: [
    ioCategory, // 입출력/변수
    logicCategory, // 논리
    loopCategory, // 반복
    mathCategory, // 수학
    textCategory, // 텍스트
    listCategory, // 리스트
    procedureCategory, // 함수
  ],
};
