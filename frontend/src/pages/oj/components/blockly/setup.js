import * as Blockly from "blockly";
import "blockly/blocks";
import * as Ko from "blockly/msg/ko";
import "./blocks";

// 블록 편집기와 보기 화면이 함께 쓰는 설정. 한국어 문구와 우리 블록을 등록한다.
Blockly.setLocale(Ko);
Blockly.Msg["TEXT_JOIN_TITLE_CREATEWITH"] = "텍스트 합치기";
Blockly.Msg["TEXT_CREATE_JOIN_TITLE_JOIN"] = "합치기";
Blockly.Msg["LOGIC_NEGATE_TITLE"] = "%1이(가) 아닙니다.";
// 함수 만들기 블록은 하나만 쓰고, 값을 돌려줄 때는 '돌려줌' 블록을 넣는다(procedureBlocks.js)
Blockly.Msg["PROCEDURES_DEFNORETURN_TOOLTIP"] = "함수를 만듭니다. 값을 돌려주려면 안에 '돌려줌' 블록을 넣습니다.";
// 새 함수 블록에 붙던 "이 함수를 설명하세요..." 메모를 없앤다. 코드 맨 위에 주석으로 그대로 나와 헷갈렸다.
Blockly.Msg["PROCEDURES_DEFNORETURN_COMMENT"] = "";
Blockly.Msg["PROCEDURES_DEFRETURN_COMMENT"] = "";
