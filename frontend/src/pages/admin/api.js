import axios from 'axios'
import { ElMessage } from 'element-plus'
import utils from '@/utils/utils'

axios.defaults.baseURL = '/api'
axios.defaults.xsrfHeaderName = 'X-CSRFToken'
axios.defaults.xsrfCookieName = 'csrftoken'

export default {
  login (username, password) {
    return ajax('login', 'post', { data: { username, password } })
  },
  logout () {
    return ajax('logout', 'get')
  },
  getProfile () {
    return ajax('profile', 'get')
  },
  getAnnouncementList (offset, limit) {
    return ajax('admin/announcement', 'get', { params: { paging: true, offset, limit } })
  },
  deleteAnnouncement (id) {
    return ajax('admin/announcement', 'delete', { params: { id } })
  },
  updateAnnouncement (data) {
    return ajax('admin/announcement', 'put', { data })
  },
  createAnnouncement (data) {
    return ajax('admin/announcement', 'post', { data })
  },
  getUserList (offset, limit, keyword) {
    let params = { paging: true, offset, limit }
    if (keyword) params.keyword = keyword
    return ajax('admin/user', 'get', { params })
  },
  getUser (id) {
    return ajax('admin/user', 'get', { params: { id } })
  },
  editUser (data) {
    return ajax('admin/user', 'put', { data })
  },
  deleteUsers (id) {
    return ajax('admin/user', 'delete', { params: { id } })
  },
  importUsers (users) {
    return ajax('admin/user', 'post', { data: { users } })
  },
  generateUser (data) {
    return ajax('admin/generate_user', 'post', { data })
  },
  getLanguages () {
    return ajax('languages', 'get')
  },
  getSMTPConfig () {
    return ajax('admin/smtp', 'get')
  },
  createSMTPConfig (data) {
    return ajax('admin/smtp', 'post', { data })
  },
  editSMTPConfig (data) {
    return ajax('admin/smtp', 'put', { data })
  },
  testSMTPConfig (email) {
    return ajax('admin/smtp_test', 'post', { data: { email } })
  },
  getWebsiteConfig () {
    return ajax('admin/website', 'get')
  },
  editWebsiteConfig (data) {
    return ajax('admin/website', 'post', { data })
  },
  getJudgeServer () {
    return ajax('admin/judge_server', 'get')
  },
  deleteJudgeServer (hostname) {
    return ajax('admin/judge_server', 'delete', { params: { hostname } })
  },
  updateJudgeServer (data) {
    return ajax('admin/judge_server', 'put', { data })
  },
  getInvalidTestCaseList () {
    return ajax('admin/prune_test_case', 'get')
  },
  pruneTestCase (id) {
    return ajax('admin/prune_test_case', 'delete', { params: { id } })
  },
  createContest (data) {
    return ajax('admin/contest', 'post', { data })
  },
  getContest (id) {
    return ajax('admin/contest', 'get', { params: { id } })
  },
  editContest (data) {
    return ajax('admin/contest', 'put', { data })
  },
  getContestList (offset, limit, keyword) {
    let params = { paging: true, offset, limit }
    if (keyword) params.keyword = keyword
    return ajax('admin/contest', 'get', { params })
  },
  getContestAnnouncementList (contestID) {
    return ajax('admin/contest/announcement', 'get', { params: { contest_id: contestID } })
  },
  createContestAnnouncement (data) {
    return ajax('admin/contest/announcement', 'post', { data })
  },
  deleteContestAnnouncement (id) {
    return ajax('admin/contest/announcement', 'delete', { params: { id } })
  },
  updateContestAnnouncement (data) {
    return ajax('admin/contest/announcement', 'put', { data })
  },
  getProblemTagList (params) {
    return ajax('problem/tags', 'get', { params })
  },
  getAdminProblemTagList (params) {
    params = utils.filterEmptyValue(params || {})
    return ajax('admin/problem/tags', 'get', { params })
  },
  createProblemTag (data) {
    return ajax('admin/problem/tags', 'post', { data })
  },
  editProblemTag (data) {
    return ajax('admin/problem/tags', 'put', { data })
  },
  deleteProblemTag (id) {
    return ajax('admin/problem/tags', 'delete', { params: { id } })
  },
  compileSPJ (data) {
    return ajax('admin/compile_spj', 'post', { data })
  },
  createProblem (data) {
    return ajax('admin/problem', 'post', { data })
  },
  editProblem (data) {
    return ajax('admin/problem', 'put', { data })
  },
  deleteProblem (id) {
    return ajax('admin/problem', 'delete', { params: { id } })
  },
  getProblem (id) {
    return ajax('admin/problem', 'get', { params: { id } })
  },
  getProblemList (params) {
    params = utils.filterEmptyValue(params)
    return ajax('admin/problem', 'get', { params })
  },
  getContestProblemList (params) {
    params = utils.filterEmptyValue(params)
    return ajax('admin/contest/problem', 'get', { params })
  },
  getContestProblem (id) {
    return ajax('admin/contest/problem', 'get', { params: { id } })
  },
  createContestProblem (data) {
    return ajax('admin/contest/problem', 'post', { data })
  },
  editContestProblem (data) {
    return ajax('admin/contest/problem', 'put', { data })
  },
  deleteContestProblem (id) {
    return ajax('admin/contest/problem', 'delete', { params: { id } })
  },
  makeContestProblemPublic (data) {
    return ajax('admin/contest_problem/make_public', 'post', { data })
  },
  addProblemFromPublic (data) {
    return ajax('admin/contest/add_problem_from_public', 'post', { data })
  },
  getReleaseNotes () {
    return ajax('admin/versions', 'get')
  },
  getDashboardInfo () {
    return ajax('admin/dashboard_info', 'get')
  },
  getSessions () {
    return ajax('sessions', 'get')
  },
  exportProblems (data) {
    return ajax('export_problem', 'post', { data })
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
          window.location.href = '/admin/login'
        }
      } else {
        resolve(res)
        if (method !== 'get') {
          ElMessage.success('완료되었습니다')
        }
      }
    }, res => {
      reject(res)
      ElMessage.error(errorMessage(res))
    })
  })
}
