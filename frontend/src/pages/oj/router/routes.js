// all routes here.
import Home from '@oj/views/general/Home.vue'
import NotFound from '@oj/views/general/404.vue'
import Announcements from '@oj/views/general/Announcements.vue'
import Logout from '@oj/views/user/Logout.vue'
import UserHome from '@oj/views/user/UserHome.vue'
import About from '@oj/views/help/About.vue'
import FAQ from '@oj/views/help/FAQ.vue'
import ProblemList from '@oj/views/problem/ProblemList.vue'

const SubmissionList = () => import('@oj/views/submission/SubmissionList.vue')
const SubmissionDetails = () => import('@oj/views/submission/SubmissionDetails.vue')
const ACMRank = () => import('@oj/views/rank/ACMRank.vue')
const OIRank = () => import('@oj/views/rank/OIRank.vue')
const ApplyResetPassword = () => import('@oj/views/user/ApplyResetPassword.vue')
const ResetPassword = () => import('@oj/views/user/ResetPassword.vue')
const Problem = () => import('@oj/views/problem/Problem.vue')

const ContestList = () => import('@oj/views/contest/ContestList.vue')
const ContestDetails = () => import('@oj/views/contest/ContestDetail.vue')
const ContestProblemList = () => import('@oj/views/contest/children/ContestProblemList.vue')
const ContestRank = () => import('@oj/views/contest/children/ContestRank.vue')
const ACMContestHelper = () => import('@oj/views/contest/children/ACMHelper.vue')

const Settings = () => import('@oj/views/setting/Settings.vue')
const ProfileSetting = () => import('@oj/views/setting/children/ProfileSetting.vue')
const SecuritySetting = () => import('@oj/views/setting/children/SecuritySetting.vue')
const TeacherSetting = () => import('@oj/views/setting/children/TeacherSetting.vue')
const TeacherClassList = () => import('@oj/views/teacher/ClassList.vue')
const TeacherClassDetail = () => import('@oj/views/teacher/ClassDetail.vue')
const TeacherProblemSetList = () => import('@oj/views/teacher/ProblemSetList.vue')
const TeacherProgressBoard = () => import('@oj/views/teacher/ProgressBoard.vue')
const TeacherStudentDetail = () => import('@oj/views/teacher/StudentDetail.vue')
const TeacherProblemSetDetail = () => import('@oj/views/teacher/ProblemSetDetail.vue')
const ProblemSetList = () => import('@oj/views/problem/ProblemSetList.vue')
const ProblemSetDetail = () => import('@oj/views/problem/ProblemSetDetail.vue')
const StudentPasswordSetting = () => import('@oj/views/setting/children/StudentPasswordSetting.vue')
const AccountSetting = () => import('@oj/views/setting/children/AccountSetting.vue')

export default [
  {
    name: 'home',
    path: '/',
    meta: { title: '홈' },
    component: Home
  },
  {
    name: 'logout',
    path: '/logout',
    meta: { title: '로그아웃' },
    component: Logout
  },
  {
    name: 'apply-reset-password',
    path: '/apply-reset-password',
    meta: { title: '비밀번호 재설정 요청' },
    component: ApplyResetPassword
  },
  {
    name: 'reset-password',
    path: '/reset-password/:token',
    meta: { title: '비밀번호 재설정' },
    component: ResetPassword
  },
  {
    name: 'problem-list',
    path: '/problem',
    meta: { title: '문제 목록' },
    component: ProblemList
  },
  {
    name: 'problem-details',
    path: '/problem/:problemID',
    meta: { title: '문제 상세' },
    component: Problem
  },
  {
    name: 'submission-list',
    path: '/status',
    meta: { title: '제출 목록' },
    component: SubmissionList
  },
  {
    name: 'submission-details',
    path: '/status/:id/',
    meta: { title: '제출 상세' },
    component: SubmissionDetails
  },
  {
    name: 'contest-list',
    path: '/contest',
    meta: { title: '대회 목록' },
    component: ContestList
  },
  {
    name: 'contest-details',
    path: '/contest/:contestID/',
    component: ContestDetails,
    meta: { title: '대회 상세' },
    children: [
      {
        name: 'contest-submission-list',
        path: 'submissions',
        component: SubmissionList
      },
      {
        name: 'contest-problem-list',
        path: 'problems',
        component: ContestProblemList
      },
      {
        name: 'contest-problem-details',
        path: 'problem/:problemID/',
        component: Problem
      },
      {
        name: 'contest-announcement-list',
        path: 'announcements',
        component: Announcements
      },
      {
        name: 'contest-rank',
        path: 'rank',
        component: ContestRank
      },
      {
        name: 'acm-helper',
        path: 'helper',
        component: ACMContestHelper
      }
    ]
  },
  {
    name: 'acm-rank',
    path: '/acm-rank',
    meta: { title: '문제 해결 순위' },
    component: ACMRank
  },
  {
    name: 'oi-rank',
    path: '/oi-rank',
    meta: { title: 'OI 순위' },
    component: OIRank
  },
  {
    name: 'user-home',
    path: '/user-home',
    component: UserHome,
    meta: { requiresAuth: true, title: '사용자 홈' }
  },
  {
    path: '/setting',
    component: Settings,
    children: [
      {
        name: 'default-setting',
        path: '',
        meta: { requiresAuth: true, title: '설정' },
        component: ProfileSetting
      },
      {
        name: 'profile-setting',
        path: 'profile',
        meta: { requiresAuth: true, title: '프로필 설정' },
        component: ProfileSetting
      },
      {
        name: 'account-setting',
        path: 'account',
        meta: { requiresAuth: true, title: '계정 설정' },
        component: AccountSetting
      },
      {
        name: 'security-setting',
        path: 'security',
        meta: { requiresAuth: true, title: '보안 설정' },
        component: SecuritySetting
      },
      {
        name: 'student-password-setting',
        path: 'password',
        meta: { requiresAuth: true, title: '비밀번호 변경' },
        component: StudentPasswordSetting
      },
      {
        name: 'teacher-setting',
        path: 'teacher',
        meta: { requiresAuth: true, title: '교사 인증' },
        component: TeacherSetting
      }
    ]
  },
  {
    path: '/teacher',
    redirect: { name: 'teacher-class-list' }
  },
  {
    path: '/teacher/class',
    name: 'teacher-class-list',
    meta: { requiresAuth: true, title: '내 학급' },
    component: TeacherClassList
  },
  {
    path: '/teacher/class/:classId',
    name: 'teacher-class-detail',
    meta: { requiresAuth: true, title: '학급 학생' },
    component: TeacherClassDetail
  },
  {
    path: '/teacher/problem-set',
    name: 'teacher-problem-set-list',
    meta: { requiresAuth: true, title: '문제집 관리' },
    component: TeacherProblemSetList
  },
  {
    path: '/teacher/problem-set/:setId',
    name: 'teacher-problem-set-detail',
    meta: { requiresAuth: true, title: '문제집' },
    component: TeacherProblemSetDetail
  },
  {
    path: '/teacher/progress',
    name: 'teacher-progress',
    meta: { requiresAuth: true, title: '학습 현황' },
    component: TeacherProgressBoard
  },
  {
    path: '/teacher/student/:membershipId',
    name: 'teacher-student-detail',
    meta: { requiresAuth: true, title: '학생 제출 기록' },
    component: TeacherStudentDetail
  },
  {
    path: '/problem-set',
    name: 'problem-set-list',
    meta: { requiresAuth: true, title: '내 문제집' },
    component: ProblemSetList
  },
  {
    path: '/problem-set/:setId',
    name: 'problem-set-detail',
    meta: { requiresAuth: true, title: '문제집' },
    component: ProblemSetDetail
  },
  {
    path: '/about',
    name: 'about',
    meta: { title: '정보' },
    component: About
  },
  {
    path: '/faq',
    name: 'faq',
    meta: { title: '자주 묻는 질문' },
    component: FAQ
  },
  {
    path: '/:pathMatch(.*)*',
    meta: { title: '404' },
    component: NotFound
  }
]
