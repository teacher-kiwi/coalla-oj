import { defineStore } from 'pinia'
import dayjs from 'dayjs'
import duration from 'dayjs/plugin/duration'
import relativeTime from 'dayjs/plugin/relativeTime'
import { CONTEST_STATUS, USER_TYPE, CONTEST_TYPE } from '@/utils/constants'
import { useUserStore } from './user'

dayjs.extend(duration)
dayjs.extend(relativeTime)

export const useContestStore = defineStore('contest', {
  state: () => ({
    now: dayjs(),
    access: false,
    rankLimit: 30,
    forceUpdate: false,
    contest: {
      created_by: {},
      contest_type: CONTEST_TYPE.PUBLIC
    },
    contestProblems: [],
    itemVisible: {
      menu: true,
      chart: true,
      realName: false
    }
  }),
  getters: {
    contestLoaded: (state) => !!state.contest.status,
    contestStatus () {
      if (!this.contestLoaded) return null
      let startTime = dayjs(this.contest.start_time)
      let endTime = dayjs(this.contest.end_time)
      if (startTime.isAfter(this.now)) return CONTEST_STATUS.NOT_START
      if (endTime.isBefore(this.now)) return CONTEST_STATUS.ENDED
      return CONTEST_STATUS.UNDERWAY
    },
    contestRuleType: (state) => state.contest.rule_type || null,
    isContestAdmin () {
      const userStore = useUserStore()
      return userStore.isAuthenticated &&
        (this.contest.created_by.id === userStore.user.id ||
          userStore.user.admin_type === USER_TYPE.SUPER_ADMIN)
    },
    contestMenuDisabled () {
      if (this.isContestAdmin) return false
      if (this.contest.contest_type === CONTEST_TYPE.PUBLIC) {
        return this.contestStatus === CONTEST_STATUS.NOT_START
      }
      return !this.access
    },
    OIContestRealTimePermission () {
      if (this.contestRuleType === 'ACM' || this.contestStatus === CONTEST_STATUS.ENDED) return true
      return this.contest.real_time_rank === true || this.isContestAdmin
    },
    problemSubmitDisabled () {
      const userStore = useUserStore()
      if (this.contestStatus === CONTEST_STATUS.ENDED) return true
      if (this.contestStatus === CONTEST_STATUS.NOT_START) return !this.isContestAdmin
      return !userStore.isAuthenticated
    },
    passwordFormVisible () {
      return this.contest.contest_type !== CONTEST_TYPE.PUBLIC &&
        !this.access && !this.isContestAdmin
    },
    contestStartTime: (state) => dayjs(state.contest.start_time),
    contestEndTime: (state) => dayjs(state.contest.end_time),
    countdown () {
      if (this.contestStatus === CONTEST_STATUS.NOT_START) {
        let dur = dayjs.duration(this.contestStartTime.diff(this.now, 'seconds'), 'seconds')
        if (dur.asWeeks() > 0) return 'Start At ' + dur.humanize()
        let texts = [Math.floor(dur.asHours()), dur.minutes(), dur.seconds()]
        return '-' + texts.join(':')
      } else if (this.contestStatus === CONTEST_STATUS.UNDERWAY) {
        let dur = dayjs.duration(this.contestEndTime.diff(this.now, 'seconds'), 'seconds')
        let texts = [Math.floor(dur.asHours()), dur.minutes(), dur.seconds()]
        return '-' + texts.join(':')
      }
      return 'Ended'
    }
  },
  actions: {
    async getContest (contestID) {
      const { default: api } = await import('@oj/api')
      const res = await api.getContest(contestID)
      let contest = res.data.data
      this.contest = contest
      this.now = dayjs(contest.now)
      if (contest.contest_type === CONTEST_TYPE.PRIVATE) {
        await this.getContestAccess(contestID)
      }
      return res
    },
    async getContestProblems (contestID) {
      const { default: api } = await import('@oj/api')
      try {
        const res = await api.getContestProblemList(contestID)
        this.contestProblems = res.data.data.sort((a, b) => {
          if (a._id === b._id) return 0
          return a._id > b._id ? 1 : -1
        })
        return res
      } catch {
        this.contestProblems = []
      }
    },
    async getContestAccess (contestID) {
      const { default: api } = await import('@oj/api')
      const res = await api.getContestAccess(contestID)
      this.access = res.data.data.access
      return res
    },
    changeContestItemVisible (payload) {
      this.itemVisible = { ...this.itemVisible, ...payload }
    },
    changeRankForceUpdate (value) {
      this.forceUpdate = value
    },
    changeRankLimit (rankLimit) {
      this.rankLimit = rankLimit
    },
    clearContest () {
      this.contest = { created_by: {} }
      this.contestProblems = []
      this.access = false
      this.itemVisible = { menu: true, chart: true, realName: false }
      this.forceUpdate = false
    },
    updateNow () {
      this.now = dayjs(this.now).add(1, 's')
    }
  }
})
