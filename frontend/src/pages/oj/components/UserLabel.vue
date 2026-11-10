<template>
  <a class="user-label link-text" @click="goProfile">
    <CharacterAvatar :username="username" :size="28" />
    <span class="name">
      <template v-if="nickname">{{ nickname }}({{ username }})</template>
      <template v-else>{{ username }}</template>
    </span>
  </a>
</template>

<script setup>
// 공개 화면(순위·채점 현황)에서 사용자를 가리키는 이름.
//
// 학생 아이디는 무작위라("학생12345678") 그대로 보여줘도 학교나 반이 드러나지
// 않는다. nickname 은 담당 교사가 목록을 볼 때만 서버가 함께 내려주므로,
// 값이 있으면 "홍길동(학생12345678)" 처럼 붙여 자기 학생을 알아보게 한다.
import { useRouter } from 'vue-router'
import CharacterAvatar from './CharacterAvatar.vue'

const props = defineProps({
  username: { type: String, required: true },
  nickname: { type: String, default: null }
})

const router = useRouter()

function goProfile () {
  router.push({ name: 'user-home', query: { username: props.username } })
}
</script>

<style scoped>
/* 이름 앞에 상반신 캐릭터. 칸이 좁으면 이름만 말줄임한다 */
.user-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  max-width: 100%;
  vertical-align: middle;
}
.name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
