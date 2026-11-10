import * as Blockly from "blockly";

// 파이썬 3 는 한글 변수 이름을 그대로 쓸 수 있다.
// Blockly 기본은 영문·숫자·_ 가 아닌 글자를 %XX 로 바꿔서 '숫자들' 이
// _EC_88_AB_EC_9E_90_EB_93_A4 가 된다. 학생이 '생성된 코드 보기'나 오류 메시지에서
// 자기 변수를 알아볼 수 없으니, 파이썬이 이름에 허용하는 글자는 그대로 둔다.
//
// 파이썬 이름에 쓸 수 있는 것: 글자(한글 포함)·숫자(0-9 등 Nd)·결합 부호·밑줄.
// ²·½ 같은 숫자 모양 기호는 이름에 못 쓰므로 \p{N} 이 아니라 \p{Nd} 만 둔다.
// 예약어·내장 함수 이름과 겹치는 것은 이 뒤에 Blockly 가 input2 처럼 피해 준다.
const NOT_ALLOWED = /[^\p{L}\p{Nd}\p{Mn}\p{Mc}_]/gu;
const original = Blockly.Names.prototype.safeName;

Blockly.Names.prototype.safeName = function (name) {
  if (!name) return original.call(this, name);
  let safe = name.replace(/ /g, "_").replace(NOT_ALLOWED, "_");
  if (/^\p{Nd}/u.test(safe)) safe = "my_" + safe;
  return safe;
};
