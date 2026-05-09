<template>
  <div class="error404">
    <div class="error404-body-con">
      <el-card>
        <div class="error404-body-con-title">4<span><el-icon><Compass /></el-icon></span>4</div>
        <p class="error404-body-con-message">YOU&nbsp;&nbsp;LOOK&nbsp;&nbsp;LOST</p>
        <div class="error404-btn-con">
          <el-button @click="goHome" size="large" class="error-btn">{{ t('m.Go_Home') }}</el-button>
          <el-button @click="backPage" size="large" class="error-btn error-btn-back" type="primary">{{ t('m.Back') }}</el-button>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Compass } from '@element-plus/icons-vue'

const router = useRouter()
const { t } = useI18n()

function backPage () {
  router.go(-1)
}
function goHome () {
  router.push({ name: 'home' })
}
</script>

<style lang="less" scoped>
  @keyframes error404animation {
    0% { transform: rotateZ(0deg); }
    20% { transform: rotateZ(-60deg); }
    40% { transform: rotateZ(-10deg); }
    60% { transform: rotateZ(50deg); }
    80% { transform: rotateZ(-20deg); }
    100% { transform: rotateZ(0deg); }
  }

  .error404 {
    &-body-con {
      width: 700px;
      height: 500px;
      margin: 0 auto;
      &-title {
        text-align: center;
        font-size: 240px;
        font-weight: 700;
        color: #2d8cf0;
        height: 260px;
        line-height: 260px;
        margin-top: 40px;
        span {
          display: inline-block;
          color: #19be6b;
          font-size: 230px;
          animation: error404animation 3s ease 0s infinite alternate;
        }
      }
      &-message {
        display: block;
        text-align: center;
        font-size: 30px;
        font-weight: 500;
        letter-spacing: 12px;
        color: #dddde2;
      }
    }
    &-btn-con {
      text-align: center;
      padding: 20px 0;
      margin-bottom: 40px;
    }
  }
  .error-btn {
    width: 200px;
    &-back {
      margin-left: 40px;
    }
  }
</style>
