<template>
  <Panel>
    <template #title>자주 묻는 질문</template>
    <div class="content markdown-body">
      <ul>
        <li>입력과 출력은 어디에 있나요?
          <p>프로그램은 <code>stdin</code> ('표준 입력') 에서 입력을 읽고 <code>stdout</code>
            ('표준 출력') 으로 출력을 써야 합니다. 예를 들어 <code>scanf</code> C에서는 <code>cin</code>
            C++에서는 stdin으로부터 읽을 수 있고 <code>printf</code> C에서는 <code>cout</code> C++에서는 stdout으로 출력할 수 있습니다. 사용자 프로그램은 파일을 읽거나 쓸 수 없으며, 그렇지 않으면 <code>런타임 에러</code>.
          </p>
        </li>
        <li>제출 실행 시간의 의미는 무엇인가요?
          <p>온라인 저지는 여러 테스트 파일로 코드를 여러 번 테스트할 수 있습니다. 각 입력 파일에 대해 시간 제한 내에 정답을 제공하면, 표시되는 실행 시간은 각 테스트 케이스에 소요된 시간의 최댓값입니다. 그렇지 않으면 실행 시간은 의미가 없습니다.</p>
        </li>
        <li>C++ Int64는 어떻게 사용하나요?
          <p>다음과 같이 선언해야 합니다<code>long long</code> 그리고 다음과 함께 사용 <code>cin/cout</code> 또는 <code>%lld</code>, 사용<code> __int64</code> 은 다음을 야기합니다 <code>컴파일 에러</code>.</p>
        </li>
        <li>Java 사양
          <p>모든 프로그램은 <code>메인</code> 클래스의 static main 메서드에서 시작해야 합니다. public 클래스를 사용하지 마세요: <code>메인</code> 도 컴파일 오류를 피하기 위해 non public이어야 합니다. 과도한 플러싱으로 인한 시간 초과를 피하기 위해 버퍼링된 I/O를 사용하세요.</p>
        </li>
        <li>출력 형식 오류에 대해
          <p>이 온라인 저지에는 출력 형식 오류가 없습니다. 채점기는 출력의 <b>마지막</b> 줄에서 공백과 줄 바꿈을 제거합니다. 그래도 정답과 다르면 결과는 <code> 오답</code>.</p>
        </li>
        <li>이 온라인 저지의 버그를 어떻게 보고하나요?
          <p>온라인 저지는 오픈 소스입니다. 다음에서 이슈를 열 수 있습니다 <a href="https://github.com/QingdaoU/OnlineJudge">Github</a>
            버그 해결에 많은 도움이 되는 환경, 버전 등의 세부 정보가 필요합니다. 물론 풀 리퀘스트를 병합해 주시면 기쁘게 생각하겠습니다.
          </p>
        </li>
      </ul>
    </div>
  </Panel>
</template>

<script setup>
</script>

<style lang="less" scoped>
  .content {
    font-size: 16px;
    margin: 0 50px 40px 50px;
    > ul {
      list-style: disc;
      li {
        font-size: 16px;
        margin-top: 20px;
        &:first-child {
          margin-top: 0;
        }
        p {
          font-size: 14px;
          margin-top: 5px;
        }
      }
    }
  }
</style>
