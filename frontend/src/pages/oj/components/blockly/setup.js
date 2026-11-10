import * as Blockly from "blockly";
import "blockly/blocks";
import * as Ko from "blockly/msg/ko";
import "./blocks";

// 블록 편집기와 보기 화면이 함께 쓰는 설정. 한국어 문구와 우리 블록을 등록한다.
Blockly.setLocale(Ko);
Blockly.Msg["TEXT_JOIN_TITLE_CREATEWITH"] = "텍스트 합치기";
Blockly.Msg["TEXT_CREATE_JOIN_TITLE_JOIN"] = "합치기";
Blockly.Msg["LOGIC_NEGATE_TITLE"] = "%1이(가) 아닙니다.";
