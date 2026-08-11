<template>
  <div>
    <Panel class="container">
      <template #title>컴파일러 & 채점기</template>
      <div class="content markdown-body">
        <ul>
          <li v-for="lang in languages" :key="lang.name">
            {{ lang.name }} ( {{ lang.description }} )
            <pre>{{ lang.config.compile.compile_command }}</pre>
          </li>
        </ul>
      </div>
    </Panel>

    <Panel :padding="15" class="container">
      <template #title>결과 설명</template>
      <div class="content">
        <ul>
          <li><b>대기 중 & 채점 중</b> : 곧 채점될 예정입니다. 결과를 기다려주세요.</li>
          <li><b>컴파일 에러</b> : 소스 코드 컴파일에 실패했습니다. 링크를 클릭하여 컴파일러 출력을 확인하세요.</li>
          <li><b>정답</b> : 축하합니다. 정답입니다.</li>
          <li><b>오답</b> : 프로그램의 출력이 정답과 일치하지 않습니다.</li>
          <li><b>런타임 에러</b> : 프로그램이 비정상적으로 종료되었습니다. 세그먼트 폴트, 0으로 나누기 또는 0이 아닌 코드로 종료했을 가능성이 있습니다.</li>
          <li><b>시간 초과</b> : 프로그램의 CPU 시간이 제한을 초과했습니다.</li>
          <li><b>메모리 초과</b> : 프로그램의 메모리 사용량이 제한을 초과했습니다.</li>
          <li><b>시스템 에러</b> : 채점 서버에 문제가 발생했습니다. 관리자에게 문의하세요.</li>
        </ul>
      </div>
    </Panel>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import utils from '@/utils/utils'
const languages = ref([])

onMounted(() => {
  utils.getLanguages().then((res) => {
    languages.value = res
  })
})
</script>

<style scoped lang="less">
  .container {
    margin-bottom: 20px;

    .content {
      font-size: 16px;
      margin: 0 50px 20px 50px;
      > ul {
        list-style: disc;
        li {
          line-height: 2;
          .title {
            font-weight: 500;
          }
        }
      }
    }
  }
</style>
