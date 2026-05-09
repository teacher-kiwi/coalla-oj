<template>
  <div />
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@oj/api'
import { useUserStore } from '@/store/user'

const router = useRouter()
const userStore = useUserStore()

onMounted(() => {
  api.logout().then(() => {
    userStore.clearProfile()
    router.replace({ path: '/' })
  })
})
</script>
