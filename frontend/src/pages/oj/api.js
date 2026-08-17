import axios from 'axios'
import { ElMessage } from 'element-plus'

axios.defaults.baseURL = '/api'
axios.defaults.xsrfHeaderName = 'X-CSRFToken'
axios.defaults.xsrfCookieName = 'csrftoken'

export default {
  getWebsiteConf (params) {
    return ajax('website', 'get', { params })
  },
  getAnnouncementList (offset, limit) {
    return ajax('announcement', 'get', { params: { offset, limit } })
  },
  login (data) {
    return ajax('login', 'post', { data })
  },
  checkUsernameOrEmail (username, email) {
    return ajax('check_username_or_email', 'post', { data: { username, email } })
  },
  register (data) {
    return ajax('register', 'post', { data })
  },
  logout () {
    return ajax('logout', 'get')
  },
  getAccountDeleteInfo () {
    return ajax('delete_account', 'get')
  },
  deleteAccount (credential) {
    return ajax('delete_account', 'post', { data: { credential } })
  },
  googleLogin (credential, nickname) {
    const data = { credential }
    if (nickname) data.nickname = nickname
    return ajax('google_login', 'post', { data })
  },
  getMyTeacherApplication () {
    return ajax('teacher_application', 'get')
  },
  applyForTeacher () {
    return ajax('teacher_application', 'post')
  },

  // ---- 학생 로그인 (로그인 전 호출) ----
  searchStudentSchool (keyword) {
    return ajax('student/school', 'get', { params: { keyword } })
  },
  getStudentClasses (schoolId) {
    return ajax('student/class', 'get', { params: { school_id: schoolId } })
  },
  studentLogin (data) {
    return ajax('student/login', 'post', { data })
  },
  studentChangePassword (data) {
    return ajax('student/change_password', 'post', { data })
  },

  // ---- 교사 ----
  searchSchool (keyword) {
    return ajax('teacher/school', 'get', { params: { keyword, paging: true, offset: 0, limit: 20 } })
  },
  getMyClasses (archived = false) {
    return ajax('teacher/class', 'get', { params: archived ? { archived: 'true' } : {} })
  },
  getClass (id) {
    return ajax('teacher/class', 'get', { params: { id } })
  },
  createClass (data) {
    return ajax('teacher/class', 'post', { data })
  },
  editClass (data) {
    return ajax('teacher/class', 'put', { data })
  },
  getClassStudents (classId) {
    return ajax('teacher/student', 'get', { params: { class_id: classId } })
  },
  createStudents (data) {
    return ajax('teacher/student', 'post', { data })
  },
  resetStudentPassword (membership) {
    return ajax('teacher/student', 'put', { data: { membership } })
  },
  deleteStudent (id) {
    return ajax('teacher/student', 'delete', { params: { id } })
  },
  // ---- 교사 출제 ----
  getMyProblems () {
    return ajax('teacher/problem', 'get')
  },
  getMyProblem (id) {
    return ajax('teacher/problem', 'get', { params: { id } })
  },
  createProblem (data) {
    return ajax('teacher/problem', 'post', { data })
  },
  editProblem (data) {
    return ajax('teacher/problem', 'put', { data })
  },
  deleteProblem (id) {
    return ajax('teacher/problem', 'delete', { params: { id } })
  },
  requestProblemPublish (id) {
    return ajax('teacher/problem/publish', 'post', { data: { id } })
  },
  cancelProblemPublish (id) {
    return ajax('teacher/problem/publish', 'delete', { params: { id } })
  },

  getMyProblemSets () {
    return ajax('teacher/problem_set', 'get')
  },
  getProblemSetForTeacher (id) {
    return ajax('teacher/problem_set', 'get', { params: { id } })
  },
  createProblemSet (data) {
    return ajax('teacher/problem_set', 'post', { data })
  },
  editProblemSet (data) {
    return ajax('teacher/problem_set', 'put', { data })
  },
  deleteProblemSet (id) {
    return ajax('teacher/problem_set', 'delete', { params: { id } })
  },
  addProblemSetProblems (problemSet, problems) {
    return ajax('teacher/problem_set/problem', 'post', { data: { problem_set: problemSet, problems } })
  },
  reorderProblemSetItems (problemSet, items) {
    return ajax('teacher/problem_set/problem', 'put', { data: { problem_set: problemSet, items } })
  },
  deleteProblemSetItem (id) {
    return ajax('teacher/problem_set/problem', 'delete', { params: { id } })
  },
  assignProblemSet (data) {
    return ajax('teacher/problem_set/assignment', 'post', { data })
  },
  editProblemSetAssignment (data) {
    return ajax('teacher/problem_set/assignment', 'put', { data })
  },
  deleteProblemSetAssignment (id) {
    return ajax('teacher/problem_set/assignment', 'delete', { params: { id } })
  },
  getProblemSetProgress (problemSet, classId) {
    return ajax('teacher/problem_set/progress', 'get', { params: { problem_set: problemSet, class_id: classId } })
  },
  getStudentSubmissions (membership, offset, limit, problemId) {
    const params = { membership, offset, limit }
    if (problemId) params.problem_id = problemId
    return ajax('teacher/student/submission', 'get', { params })
  },

  // ---- 학생 문제집 ----
  getMyAssignedProblemSets () {
    return ajax('problem_sets', 'get')
  },
  getAssignedProblemSet (id) {
    return ajax('problem_set', 'get', { params: { id } })
  },
  getCaptcha () {
    return ajax('captcha', 'get')
  },
  getUserInfo (username = undefined) {
    return ajax('profile', 'get', { params: { username } })
  },
  updateProfile (profile) {
    return ajax('profile', 'put', { data: profile })
  },
  freshDisplayID (userID) {
    return ajax('profile/fresh_display_id', 'get', { params: { user_id: userID } })
  },
  getSessions () {
    return ajax('sessions', 'get')
  },
  deleteSession (sessionKey) {
    return ajax('sessions', 'delete', { params: { session_key: sessionKey } })
  },
  applyResetPassword (data) {
    return ajax('apply_reset_password', 'post', { data })
  },
  resetPassword (data) {
    return ajax('reset_password', 'post', { data })
  },
  changePassword (data) {
    return ajax('change_password', 'post', { data })
  },
  changeEmail (data) {
    return ajax('change_email', 'post', { data })
  },
  getLanguages () {
    return ajax('languages', 'get')
  },
  getProblemTagList () {
    return ajax('problem/tags', 'get')
  },
  // 출제 화면에서 붙일 태그를 고를 때는 아직 문제가 없는 태그도 보여야 한다
  getAllProblemTags () {
    return ajax('problem/tags', 'get', { params: { all: 1 } })
  },
  getProblemList (offset, limit, searchParams) {
    let params = { paging: true, offset, limit }
    Object.keys(searchParams).forEach((element) => {
      if (searchParams[element]) {
        params[element] = searchParams[element]
      }
    })
    return ajax('problem', 'get', { params })
  },
  pickone () {
    return ajax('pickone', 'get')
  },
  getProblem (problemID) {
    return ajax('problem', 'get', { params: { problem_id: problemID } })
  },
  getContestList (offset, limit, searchParams) {
    let params = { offset, limit }
    if (searchParams !== undefined) {
      Object.keys(searchParams).forEach((element) => {
        if (searchParams[element]) {
          params[element] = searchParams[element]
        }
      })
    }
    return ajax('contests', 'get', { params })
  },
  getContest (id) {
    return ajax('contest', 'get', { params: { id } })
  },
  getContestAccess (contestID) {
    return ajax('contest/access', 'get', { params: { contest_id: contestID } })
  },
  checkContestPassword (contestID, password) {
    return ajax('contest/password', 'post', { data: { contest_id: contestID, password } })
  },
  getContestAnnouncementList (contestId) {
    return ajax('contest/announcement', 'get', { params: { contest_id: contestId } })
  },
  getContestProblemList (contestId) {
    return ajax('contest/problem', 'get', { params: { contest_id: contestId } })
  },
  getContestProblem (problemID, contestID) {
    return ajax('contest/problem', 'get', { params: { contest_id: contestID, problem_id: problemID } })
  },
  submitCode (data) {
    return ajax('submission', 'post', { data })
  },
  getSubmissionList (offset, limit, params) {
    params.limit = limit
    params.offset = offset
    return ajax('submissions', 'get', { params })
  },
  getContestSubmissionList (offset, limit, params) {
    params.limit = limit
    params.offset = offset
    return ajax('contest_submissions', 'get', { params })
  },
  getSubmission (id) {
    return ajax('submission', 'get', { params: { id } })
  },
  submissionExists (problemID) {
    return ajax('submission_exists', 'get', { params: { problem_id: problemID } })
  },
  submissionRejudge (id) {
    return ajax('admin/submission/rejudge', 'get', { params: { id } })
  },
  getUserRank (offset, limit, rule = 'acm', myStudents = false) {
    const params = { offset, limit, rule }
    if (myStudents) params.my_students = 1
    return ajax('user_rank', 'get', { params })
  },
  getContestRank (params) {
    return ajax('contest_rank', 'get', { params })
  },
  getACMACInfo (params) {
    return ajax('admin/contest/acm_helper', 'get', { params })
  },
  updateACInfoCheckedStatus (data) {
    return ajax('admin/contest/acm_helper', 'put', { data })
  }
}

// 로그인 필요 여부는 미들웨어의 에러 코드로 판정한다. 데코레이터가 내려주는
// 일반 error 응답도 있어 메시지 접두사를 함께 본다.
function isLoginRequired (res, detail) {
  if (res && res.data && res.data.error === 'login-required') return true
  return typeof detail === 'string' && detail.startsWith('먼저 로그인')
}

// 에러 본문이 항상 문자열인 건 아니고(직렬화 에러는 객체다), 네트워크 오류면
// res.data 자체가 없다. 에러 처리 중에 다시 예외가 나지 않도록 문자열로 정규화한다.
function errorMessage (res) {
  const detail = res && res.data && res.data.data
  if (typeof detail === 'string') return detail
  if (detail) return JSON.stringify(detail)
  return (res && res.message) || '네트워크 오류가 발생했습니다'
}

function ajax (url, method, options) {
  if (options !== undefined) {
    var { params = {}, data = {} } = options
  } else {
    params = data = {}
  }
  return new Promise((resolve, reject) => {
    axios({ url, method, params, data }).then(res => {
      if (res.data.error !== null) {
        const detail = errorMessage(res)
        ElMessage.error(detail)
        reject(res)
        if (isLoginRequired(res, detail)) {
          import('@/store/app').then(({ useAppStore }) => {
            useAppStore().changeModalStatus({ visible: true })
          })
        }
      } else {
        resolve(res)
      }
    }, res => {
      reject(res)
      ElMessage.error(errorMessage(res))
    })
  })
}
