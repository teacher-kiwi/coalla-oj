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
  twoFactorAuth (method, data) {
    return ajax('two_factor_auth', method, { data })
  },
  tfaRequiredCheck (username) {
    return ajax('tfa_required', 'post', { data: { username } })
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
  updateSubmission (data) {
    return ajax('submission', 'put', { data })
  },
  getUserRank (offset, limit, rule = 'acm') {
    return ajax('user_rank', 'get', { params: { offset, limit, rule } })
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

// 에러 본문이 항상 문자열인 건 아니고(직렬화 에러는 객체다), 네트워크 오류면
// res.data 자체가 없다. 에러 처리 중에 다시 예외가 나지 않도록 문자열로 정규화한다.
function errorMessage (res) {
  const detail = res && res.data && res.data.data
  if (typeof detail === 'string') return detail
  if (detail) return JSON.stringify(detail)
  return (res && res.message) || 'Network error'
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
        if (detail.startsWith('Please login')) {
          import('@/store/app').then(({ useAppStore }) => {
            useAppStore().changeModalStatus({ mode: 'login', visible: true })
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
