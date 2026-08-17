// label 은 화면에 표시할 한국어 이름, name 은 API/내부 식별용 영문 이름이다.
export const JUDGE_STATUS = {
  '-2': {
    name: 'Compile Error',
    label: '컴파일 에러',
    short: 'CE',
    color: 'yellow',
    type: 'warning'
  },
  '-1': {
    name: 'Wrong Answer',
    label: '오답',
    short: 'WA',
    color: 'red',
    type: 'danger'
  },
  '0': {
    name: 'Accepted',
    label: '정답',
    short: 'AC',
    color: 'green',
    type: 'success'
  },
  '1': {
    name: 'Time Limit Exceeded',
    label: '시간 초과',
    short: 'TLE',
    color: 'red',
    type: 'danger'
  },
  '2': {
    name: 'Time Limit Exceeded',
    label: '시간 초과',
    short: 'TLE',
    color: 'red',
    type: 'danger'
  },
  '3': {
    name: 'Memory Limit Exceeded',
    label: '메모리 초과',
    short: 'MLE',
    color: 'red',
    type: 'danger'
  },
  '4': {
    name: 'Runtime Error',
    label: '런타임 에러',
    short: 'RE',
    color: 'red',
    type: 'danger'
  },
  '5': {
    name: 'System Error',
    label: '시스템 에러',
    short: 'SE',
    color: 'red',
    type: 'danger'
  },
  '6': {
    name: 'Pending',
    label: '대기 중',
    color: 'yellow',
    type: 'warning'
  },
  '7': {
    name: 'Judging',
    label: '채점 중',
    color: 'blue',
    type: 'info'
  },
  '8': {
    name: 'Partial Accepted',
    label: '부분 정답',
    short: 'PAC',
    color: 'blue',
    type: 'info'
  },
  '9': {
    name: 'Submitting',
    label: '제출 중',
    color: 'yellow',
    type: 'warning'
  }
}

export const CONTEST_STATUS = {
  'NOT_START': '1',
  'UNDERWAY': '0',
  'ENDED': '-1'
}

export const CONTEST_STATUS_REVERSE = {
  '1': {
    name: 'Not Started',
    label: '시작 전',
    color: 'yellow'
  },
  '0': {
    name: 'Underway',
    label: '진행 중',
    color: 'green'
  },
  '-1': {
    name: 'Ended',
    label: '종료',
    color: 'red'
  }
}

// 서버가 내려주는 영문 값에 대응하는 화면 표시용 한국어 라벨
// 난이도 6단계. DB 에는 L1~L6 만 저장하고 이름·색은 여기서 붙인다.
// 색은 solved.ac 티어 색을 빌려왔다(브론즈→루비). 이름은 초등에서 통하는 말로 쓴다.
export const DIFFICULTY = [
  { value: 'L1', label: '입문', color: '#ad5600' },
  { value: 'L2', label: '기초', color: '#435f7a' },
  { value: 'L3', label: '기본', color: '#ec9a00' },
  { value: 'L4', label: '응용', color: '#27e2a4' },
  { value: 'L5', label: '심화', color: '#00b4fc' },
  { value: 'L6', label: '도전', color: '#ff0062' }
]

export const DIFFICULTY_LABEL = Object.fromEntries(
  DIFFICULTY.map(d => [d.value, d.label]))

export const DIFFICULTY_COLOR = Object.fromEntries(
  DIFFICULTY.map(d => [d.value, d.color]))

// 난이도를 고를 때 무엇을 뜻하는지. 출제 화면에서 안내로 보여준다.
export const DIFFICULTY_GUIDE = {
  L1: '입력을 그대로 출력하거나 사칙연산 한 번',
  L2: '조건문 하나 또는 반복문 하나',
  L3: '조건과 반복을 함께 사용',
  L4: '리스트나 문자열을 다룸',
  L5: '중첩 반복, 여러 단계를 조합',
  L6: '위 범위를 넘어서는 것'
}

export const RULE_TYPE_LABEL = {
  ACM: 'ACM',
  OI: 'OI'
}

export const CONTEST_TYPE_LABEL = {
  'Public': '공개',
  'Password Protected': '비밀번호 보호'
}

export const RULE_TYPE = {
  ACM: 'ACM',
  OI: 'OI'
}

export const CONTEST_TYPE = {
  PUBLIC: 'Public',
  PRIVATE: 'Password Protected'
}

export const USER_TYPE = {
  REGULAR_USER: 'Regular User',
  TEACHER: 'Teacher',
  ADMIN: 'Admin',
  SUPER_ADMIN: 'Super Admin'
}

export const PROBLEM_PERMISSION = {
  NONE: 'None',
  OWN: 'Own',
  ALL: 'All'
}

export const STORAGE_KEY = {
  AUTHED: 'authed',
  PROBLEM_CODE: 'problemCode',
  languages: 'languages'
}

export function buildProblemCodeKey (problemID, contestID = null) {
  if (contestID) {
    return `${STORAGE_KEY.PROBLEM_CODE}_${contestID}_${problemID}`
  }
  return `${STORAGE_KEY.PROBLEM_CODE}_NaN_${problemID}`
}
