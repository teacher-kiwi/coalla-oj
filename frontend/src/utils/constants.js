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
export const DIFFICULTY_LABEL = {
  Low: '낮음',
  Mid: '중간',
  High: '높음'
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
