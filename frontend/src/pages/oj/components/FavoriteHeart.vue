<template>
  <!-- Element Plus 아이콘에는 하트가 없어 직접 그린다.
       속을 채우거나(담아둠) 테두리만 남긴다(안 담음). 같은 모양이라 눈이 덜 흔들린다. -->
  <svg class="favorite-heart" :class="{ on }" viewBox="0 0 24 24" :width="size" :height="size"
       role="button" :aria-label="on ? '즐겨찾기 해제' : '즐겨찾기'" :aria-pressed="on"
       @click.stop="$emit('toggle')">
    <path :fill="on ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="1.8"
          d="M12 20.7 3.9 12.6a5.1 5.1 0 0 1 7.2-7.2l.9.9.9-.9a5.1 5.1 0 0 1 7.2 7.2z" />
  </svg>
</template>

<script setup>
defineProps({
  on: { type: Boolean, default: false },
  size: { type: Number, default: 18 }
})
defineEmits(['toggle'])
</script>

<style scoped>
.favorite-heart {
  cursor: pointer;
  vertical-align: -0.125em;
  color: #c0c4cc;
  transition: color .15s;
}

.favorite-heart:hover {
  color: #f56c6c;
}

.favorite-heart.on {
  color: #f56c6c;
}
</style>
