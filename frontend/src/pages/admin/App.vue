<template>
  <div id="app">
    <router-view />
  </div>
</template>

<script setup>
</script>

<style lang="less">
  // 나머지 body 규칙(여백·글꼴)은 common.less 에 있다. 여기서는 관리자만 다른 것만 덮는다.
  body {
    font-size: 14px;
    background-color: #324157;
  }

  #app {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 100%;
  }
</style>
