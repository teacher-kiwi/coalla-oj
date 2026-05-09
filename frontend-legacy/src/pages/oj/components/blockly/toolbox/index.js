import { ioCategory } from "./ioCategory";
import { logicCategory } from "./logicCategory";
import { loopCategory } from "./loopCategory";
import { mathCategory } from "./mathCategory";
import { textCategory } from "./textCategory";
import { listCategory } from "./listCategory";
import { variablesCategory } from "./variablesCategory";
import { procedureCategory } from "./procedureCategory";

export const toolboxConfig = {
  kind: "categoryToolbox",
  contents: [
    ioCategory, // 입출력
    logicCategory, // 논리
    loopCategory, // 반복
    mathCategory, // 수학
    textCategory, // 텍스트
    listCategory, // 리스트
    variablesCategory, // 변수
    procedureCategory, // 함수
  ],
};
