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
const AccountSetting = () => import('@oj/views/setting/children/AccountSetting.vue')

export default [
  {
    name: 'home',
    path: '/',
    meta: { title: 'Home' },
    component: Home
  },
  {
    name: 'logout',
    path: '/logout',
    meta: { title: 'Logout' },
    component: Logout
  },
  {
    name: 'apply-reset-password',
    path: '/apply-reset-password',
    meta: { title: 'Apply Reset Password' },
    component: ApplyResetPassword
  },
  {
    name: 'reset-password',
    path: '/reset-password/:token',
    meta: { title: 'Reset Password' },
    component: ResetPassword
  },
  {
    name: 'problem-list',
    path: '/problem',
    meta: { title: 'Problem List' },
    component: ProblemList
  },
  {
    name: 'problem-details',
    path: '/problem/:problemID',
    meta: { title: 'Problem Details' },
    component: Problem
  },
  {
    name: 'submission-list',
    path: '/status',
    meta: { title: 'Submission List' },
    component: SubmissionList
  },
  {
    name: 'submission-details',
    path: '/status/:id/',
    meta: { title: 'Submission Details' },
    component: SubmissionDetails
  },
  {
    name: 'contest-list',
    path: '/contest',
    meta: { title: 'Contest List' },
    component: ContestList
  },
  {
    name: 'contest-details',
    path: '/contest/:contestID/',
    component: ContestDetails,
    meta: { title: 'Contest Details' },
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
    meta: { title: 'ACM Rankings' },
    component: ACMRank
  },
  {
    name: 'oi-rank',
    path: '/oi-rank',
    meta: { title: 'OI Rankings' },
    component: OIRank
  },
  {
    name: 'user-home',
    path: '/user-home',
    component: UserHome,
    meta: { requiresAuth: true, title: 'User Home' }
  },
  {
    path: '/setting',
    component: Settings,
    children: [
      {
        name: 'default-setting',
        path: '',
        meta: { requiresAuth: true, title: 'Default Settings' },
        component: ProfileSetting
      },
      {
        name: 'profile-setting',
        path: 'profile',
        meta: { requiresAuth: true, title: 'Profile Settings' },
        component: ProfileSetting
      },
      {
        name: 'account-setting',
        path: 'account',
        meta: { requiresAuth: true, title: 'Account Settings' },
        component: AccountSetting
      },
      {
        name: 'security-setting',
        path: 'security',
        meta: { requiresAuth: true, title: 'Security Settings' },
        component: SecuritySetting
      }
    ]
  },
  {
    path: '/about',
    name: 'about',
    meta: { title: 'About' },
    component: About
  },
  {
    path: '/faq',
    name: 'faq',
    meta: { title: 'FAQ' },
    component: FAQ
  },
  {
    path: '/:pathMatch(.*)*',
    meta: { title: '404' },
    component: NotFound
  }
]
