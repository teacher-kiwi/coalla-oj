<template>
  <el-card :shadow="shadowMode" :body-style="{ padding: padding + 'px' }" class="panel">
    <template #header>
      <div class="panel-header">
        <div class="panel-title">
          <slot name="title"></slot>
        </div>
        <div class="panel-extra">
          <slot name="extra"></slot>
        </div>
      </div>
    </template>
    <div class="panel-body">
      <slot></slot>
    </div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  shadow: { type: Boolean, default: false },
  // 기본은 0 이다. 표만 담은 화면이 대부분이고, 표는 카드 끝까지 차는 것이 자연스럽다.
  // 표가 아닌 것(폼·설명·안내)을 담을 때는 20 을 줘서 제목과 줄을 맞춘다.
  padding: { type: Number, default: 0 },
  disHover: { type: Boolean, default: false },
  bordered: { type: Boolean, default: true }
})

const shadowMode = computed(() => (props.shadow ? 'always' : 'never'))
</script>

<style lang="less">
  @import (reference) '../../../styles/common.less';

  .panel {
    .panel-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .panel-title {
      .section-title;
      // 좌우 여백은 카드(el-card__header)가 이미 갖고 있다. 여기서 더 주면
      // 제목만 안쪽으로 들어가 본문과 어긋난다.
      padding: 5px 0;
    }
    .panel-extra {
      line-height: 40px;
      // 걸러내기 줄. 드롭다운·스위치·입력칸·버튼이 섞여 있어 높이가 제각각이다.
      // 예전에는 항목이 inline-block 이라 글자 밑선(baseline)끼리 맞았는데,
      // 높이가 다르면 밑선을 맞출수록 세로 가운데가 어긋나 드롭다운만 위로 떠 보였다.
      // flex 로 바꿔 높이와 무관하게 가운데로 맞춘다.
      ul.filter {
        display: flex;
        align-items: center;
        // 좁아지면 줄을 바꾼다(inline-block 일 때의 동작을 유지한다)
        flex-wrap: wrap;
        // 목록 기본값(위아래 여백과 왼쪽 들여쓰기)을 지운다
        margin: 0;
        padding: 0;
        list-style: none;
        // 항목 안쪽도 가운데로 맞춘다. el-dropdown 은 Element Plus 가
        // vertical-align: top 을 직접 걸어두어, 상속된 line-height 40px 이 만든
        // 줄 상자 안에서 위로 붙는다. li 를 flex 로 만들면 그 정렬 규칙이
        // 적용되지 않고 align-items 가 대신 결정한다.
        > li {
          display: flex;
          align-items: center;
          padding: 0 10px;
        }
      }
    }
    .panel-body {
      word-break: break-all;
      word-wrap: break-word;
    }
  }
</style>
