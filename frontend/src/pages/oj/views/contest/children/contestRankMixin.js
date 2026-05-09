import { ref, computed, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import api from '@oj/api'
import { CONTEST_STATUS } from '@/utils/constants'
import { useContestStore } from '@/store/contest'

export function useContestRank () {
  const route = useRoute()
  const contestStore = useContestStore()

  let refreshFunc = null
  const chartLoading = ref(false)

  const contest = computed(() => contestStore.contest)
  const contestProblems = computed(() => contestStore.contestProblems)
  const isContestAdmin = computed(() => contestStore.isContestAdmin)

  const showChart = computed({
    get: () => contestStore.itemVisible.chart,
    set: (value) => contestStore.changeContestItemVisible({ chart: value })
  })

  const showMenu = computed({
    get: () => contestStore.itemVisible.menu,
    set: (value) => contestStore.changeContestItemVisible({ menu: value })
  })

  const showRealName = computed({
    get: () => contestStore.itemVisible.realName,
    set: (value) => contestStore.changeContestItemVisible({ realName: value })
  })

  const forceUpdate = computed({
    get: () => contestStore.forceUpdate,
    set: (value) => contestStore.changeRankForceUpdate(value)
  })

  const limit = computed({
    get: () => contestStore.rankLimit,
    set: (value) => contestStore.changeRankLimit(value)
  })

  const refreshDisabled = computed(() => contestStore.contestStatus === CONTEST_STATUS.ENDED)

  function getContestRankData (page, applyToChart, applyToTable) {
    const offset = (page - 1) * limit.value
    chartLoading.value = true
    const params = {
      offset,
      limit: limit.value,
      contest_id: route.params.contestID,
      force_refresh: forceUpdate.value ? '1' : '0'
    }
    return api.getContestRank(params).then(res => {
      chartLoading.value = false
      const total = res.data.data.total
      if (page === 1) {
        applyToChart(res.data.data.results.slice(0, 10))
      }
      applyToTable(res.data.data.results)
      return total
    }).catch(() => {
      chartLoading.value = false
    })
  }

  function handleAutoRefresh (status, page, getData) {
    if (status === true) {
      refreshFunc = setInterval(() => {
        getData(1, true)
      }, 10000)
    } else {
      clearInterval(refreshFunc)
    }
  }

  function getContestProblems (contestID) {
    return contestStore.getContestProblems(contestID)
  }

  onBeforeUnmount(() => {
    clearInterval(refreshFunc)
  })

  return {
    contest,
    contestProblems,
    isContestAdmin,
    showChart,
    showMenu,
    showRealName,
    forceUpdate,
    limit,
    refreshDisabled,
    chartLoading,
    getContestRankData,
    handleAutoRefresh,
    getContestProblems
  }
}
