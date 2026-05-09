<template>
  <div class="page">
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
const props = defineProps({
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
  .page {
    margin: 20px;
    float: right;
  }
</style>
