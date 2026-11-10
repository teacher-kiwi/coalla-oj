import { createRouter, createWebHistory } from 'vue-router'
import {
  Announcement, Conf, Contest, ContestList, Home, JudgeServer, Login,
  Problem, ProblemList, ProblemTags, ProblemPublishReview, User, PruneTestCase, Dashboard,
  ProblemImportOrExport,
  TeacherApplication
} from './views'

// 캐릭터 공방은 그리기 코드가 커서 들어갈 때 따로 받는다
const ItemList = () => import('./views/character/ItemList.vue')
const ItemEditor = () => import('./views/character/ItemEditor.vue')

const router = createRouter({
  history: createWebHistory('/admin/'),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: Login
    },
    {
      path: '/',
      component: Home,
      children: [
        { path: '', name: 'dashboard', component: Dashboard },
        { path: '/announcement', name: 'announcement', component: Announcement },
        { path: '/user', name: 'user', component: User },
        { path: '/teacher-application', name: 'teacher-application', component: TeacherApplication },
        { path: '/conf', name: 'conf', component: Conf },
        { path: '/judge-server', name: 'judge-server', component: JudgeServer },
        { path: '/prune-test-case', name: 'prune-test-case', component: PruneTestCase },
        { path: '/problems', name: 'problem-list', component: ProblemList },
        { path: '/problem/tags', name: 'problem-tags', component: ProblemTags },
        { path: '/problem/publish-review', name: 'problem-publish-review',
          component: ProblemPublishReview },
        { path: '/problem/create', name: 'create-problem', component: Problem },
        { path: '/problem/edit/:problemId', name: 'edit-problem', component: Problem },
        { path: '/problem/batch_ops', name: 'problem_batch_ops', component: ProblemImportOrExport },
        { path: '/contest/create', name: 'create-contest', component: Contest },
        { path: '/contest', name: 'contest-list', component: ContestList },
        { path: '/contest/:contestId/edit', name: 'edit-contest', component: Contest },
        { path: '/contest/:contestId/announcement', name: 'contest-announcement', component: Announcement },
        { path: '/contest/:contestId/problems', name: 'contest-problem-list', component: ProblemList },
        { path: '/character', name: 'avatar-item-list', component: ItemList },
        { path: '/character/create', name: 'create-avatar-item', component: ItemEditor },
        { path: '/character/:itemId/edit', name: 'edit-avatar-item', component: ItemEditor }
      ]
    },
    { path: '/:pathMatch(.*)*', redirect: '/login' }
  ]
})

export default router
