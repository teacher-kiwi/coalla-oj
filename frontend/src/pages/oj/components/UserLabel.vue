<template>
  <a class="link-text truncate" @click="goProfile">
    <template v-if="nickname">{{ nickname }}({{ username }})</template>
    <template v-else>{{ username }}</template>
  </a>
</template>

<script setup>
// 공개 화면(순위·채점 현황)에서 사용자를 가리키는 이름.
//
// 학생 아이디는 무작위라("학생12345678") 그대로 보여줘도 학교나 반이 드러나지
// 않는다. nickname 은 담당 교사가 목록을 볼 때만 서버가 함께 내려주므로,
// 값이 있으면 "홍길동(학생12345678)" 처럼 붙여 자기 학생을 알아보게 한다.
import { useRouter } from 'vue-router'

const props = defineProps({
  username: { type: String, required: true },
  nickname: { type: String, default: null }
})

const router = useRouter()

function goProfile () {
  router.push({ name: 'user-home', query: { username: props.username } })
}
</script>
