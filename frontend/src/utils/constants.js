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

// tag 는 el-tag 의 type 이다. 화면마다 따로 정하다 값이 갈렸고(교사 목록은 종료를
// 빈 문자열로 두어 el-tag 가 막았다) 여기로 모았다.
export const CONTEST_STATUS_REVERSE = {
  '1': {
    name: 'Not Started',
    label: '시작 전',
    tag: 'warning'
  },
  '0': {
    name: 'Underway',
    label: '진행 중',
    tag: 'success'
  },
  '-1': {
    name: 'Ended',
    label: '종료',
    tag: 'info'
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

// 학급 안에서만 쓰이는지, 밖에 공개되는지. 문제와 대회가 같은 축이라
// 이름과 색을 여기서 한 번만 정한다. 화면에서는 ScopeTag 로 그린다.
// 키가 둘인 이유: 문제 API 는 visibility 로 'private' 을 주고,
// 대회는 is_class_contest 라 부르는 쪽에서 'class' 로 넘긴다.
export const SCOPE_TAG = {
  private: { label: '학급', type: 'info' },
  class: { label: '학급', type: 'info' },
  pending: { label: '승인 대기', type: 'warning' },
  public: { label: '공개', type: 'success' }
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

// 화면에 보여줄 이름. DB 에 저장되는 값은 영어라 그대로 찍으면 관리자 화면만 영어가 된다.
// 목록과 선택 상자가 같은 표를 쓰게 해서 표기가 갈라지지 않게 한다.
export const USER_TYPE_LABEL = {
  [USER_TYPE.REGULAR_USER]: '일반 사용자',
  [USER_TYPE.TEACHER]: '교사',
  [USER_TYPE.ADMIN]: '관리자',
  [USER_TYPE.SUPER_ADMIN]: '최고 관리자'
}

export const PROBLEM_PERMISSION = {
  NONE: 'None',
  OWN: 'Own',
  ALL: 'All'
}

export const PROBLEM_PERMISSION_LABEL = {
  [PROBLEM_PERMISSION.NONE]: '없음',
  [PROBLEM_PERMISSION.OWN]: '본인 문제',
  [PROBLEM_PERMISSION.ALL]: '전체'
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
