<template>
  <el-card :body-style="{ padding: 0, height: '100%' }" class="info-card">
    <el-row type="flex" class="info-card-container">
      <el-col :span="8" :style="{ 'background-color': color }" class="height-100">
        <el-icon :size="parseInt(iconSize)" class="info-card-icon">
          <component :is="icon" />
        </el-icon>
      </el-col>
      <el-col :span="16" class="info-card-text">
        <p :style="textStyle">{{ value }}</p>
        <p class="info-message">{{ message }}</p>
      </el-col>
    </el-row>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  value: { type: [String, Number], default: '' },
  color: { type: String, default: '' },
  message: { type: String, default: '' },
  icon: { type: [String, Object], default: '' },
  iconSize: { type: String, default: '35px' },
  countSize: { type: String, default: '25px' },
  countWeight: { type: Number, default: 700 }
})

const textStyle = computed(() => ({
  'font-size': props.countSize,
  'font-weight': props.countWeight,
  color: props.color
}))
</script>

<style lang="less" scoped>
  @card-height: 90px;
  .height-100 {
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .info-card {
    display: inline-block;
    margin-right: 10px;
    width: 250px;
    height: @card-height;
    text-align: center;
    vertical-align: middle;

    &-container {
      height: 100%;
      align-items: center;
      justify-content: center;
    }
    &-icon {
      line-height: @card-height;
      color: white;
    }
    &-text {
      p {
        margin: 0;
      }
      .info-message {
        font-weight: 300;
      }
    }
  }
</style>
