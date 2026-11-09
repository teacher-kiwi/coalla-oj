<template>
  <!-- 한 쪽에 다 들어가면 넘길 쪽이 없다. 빈 목록 밑에 "1" 만 뜨는 것도 막는다. -->
  <div v-if="total > pageSize || (showSizer && total > 10)" class="page">
    <el-pagination
      background
      :total="total"
      :page-size="pageSize"
      :page-sizes="[10, 30, 50, 100, 200]"
      :current-page="current"
      :layout="showSizer ? 'sizes, prev, pager, next, jumper' : 'prev, pager, next, jumper'"
      @current-change="onChange"
      @size-change="onPageSizeChange"
    />
  </div>
</template>

<script setup>
defineProps({
  total: { type: Number, required: true },
  pageSize: { type: Number, default: 10 },
  showSizer: { type: Boolean, default: false },
  current: { type: Number, default: 1 }
})

const emit = defineEmits(['update:current', 'update:pageSize', 'on-change', 'on-page-size-change'])

function onChange (page) {
  if (page < 1) page = 1
  emit('update:current', page)
  emit('on-change', page)
}

function onPageSizeChange (size) {
  emit('update:pageSize', size)
  emit('on-page-size-change', size)
}
</script>

<style scoped lang="less">
  // 카드 안 표 바로 밑에 오른쪽으로 붙인다. 예전에는 float 이라 카드 밖에 두면
  // 회색 바탕에 떠 있었고, 화면마다 카드 안·밖이 섞여 있었다.
  .page {
    display: flex;
    justify-content: flex-end;
    padding: 14px 20px;
    :deep(.el-pagination) {
      flex-wrap: wrap;
      justify-content: flex-end;
      row-gap: 8px;
    }
  }
</style>
