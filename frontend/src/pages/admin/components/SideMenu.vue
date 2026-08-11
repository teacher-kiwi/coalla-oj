<template>
  <el-menu class="vertical_menu" router :default-active="currentPath">
    <div class="logo">
      <img src="@/assets/logo.svg" alt="oj admin" />
    </div>
    <el-menu-item index="/">
      <el-icon><Odometer /></el-icon>
      대시보드
    </el-menu-item>
    <el-sub-menu v-if="userStore.isSuperAdmin" index="general">
      <template #title>
        <el-icon><Menu /></el-icon>
        일반
      </template>
      <el-menu-item index="/user">사용자</el-menu-item>
      <el-menu-item index="/announcement">공지사항</el-menu-item>
      <el-menu-item index="/conf">시스템 설정</el-menu-item>
      <el-menu-item index="/judge-server">채점 서버</el-menu-item>
      <el-menu-item index="/prune-test-case">테스트 케이스 정리</el-menu-item>
    </el-sub-menu>
    <el-sub-menu v-if="userStore.hasProblemPermission" index="problem">
      <template #title>
        <el-icon><Document /></el-icon>
        문제
      </template>
      <el-menu-item index="/problems">문제 목록</el-menu-item>
      <el-menu-item v-if="userStore.isSuperAdmin" index="/problem/tags">문제 태그</el-menu-item>
      <el-menu-item index="/problem/create">문제 생성</el-menu-item>
      <el-menu-item index="/problem/batch_ops">문제 내보내기/가져오기</el-menu-item>
    </el-sub-menu>
    <el-sub-menu index="contest">
      <template #title>
        <el-icon><Trophy /></el-icon>
        대회
      </template>
      <el-menu-item index="/contest">대회 목록</el-menu-item>
      <el-menu-item index="/contest/create">대회 생성</el-menu-item>
    </el-sub-menu>
  </el-menu>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useUserStore } from '@/store/user'
const route = useRoute()
const userStore = useUserStore()
const currentPath = ref('')

onMounted(() => {
  currentPath.value = route.path
})
</script>

<style scoped lang="less">
  .vertical_menu {
    overflow: auto;
    width: 205px;
    height: 100%;
    position: fixed !important;
    z-index: 100;
    top: 0;
    bottom: 0;
    left: 0;
    .logo {
      margin: 20px 0;
      text-align: center;
      img {
        background-color: #fff;
        border-radius: 50%;
        border: 3px solid #fff;
        width: 75px;
        height: 75px;
      }
    }
  }
</style>
