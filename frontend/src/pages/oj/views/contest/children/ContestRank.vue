<template>
  <div>
    <ACMContestRank v-if="contestRuleType === 'ACM'" />
    <OIContestRank v-else-if="contestRuleType === 'OI'" />
    <div v-else></div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import ACMContestRank from './ACMContestRank.vue'
import OIContestRank from './OIContestRank.vue'
import { useContestStore } from '@/store/contest'

const contestStore = useContestStore()

const contestRuleType = computed(() => contestStore.contestRuleType)

onBeforeRouteLeave(() => {
  contestStore.changeContestItemVisible({ menu: true })
})
</script>
