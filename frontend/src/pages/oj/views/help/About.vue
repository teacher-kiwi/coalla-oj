<template>
  <div>
    <Panel class="container">
      <template #title>{{ t('m.Compiler') }} & {{ t('m.Judger') }}</template>
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
      <template #title>{{ t('m.Result_Explanation') }}</template>
      <div class="content">
        <ul>
          <li><b>{{ t('m.Pending') }} & {{ t('m.Judging') }}</b> : {{ t('m.Pending_Judging_Description') }}</li>
          <li><b>{{ t('m.Compile_Error') }}</b> : {{ t('m.Compile_Error_Description') }}</li>
          <li><b>{{ t('m.Accepted') }}</b> : {{ t('m.Accepted_Description') }}</li>
          <li><b>{{ t('m.Wrong_Answer') }}</b> : {{ t('m.Wrong_Answer_Description') }}</li>
          <li><b>{{ t('m.Runtime_Error') }}</b> : {{ t('m.Runtime_Error_Description') }}</li>
          <li><b>{{ t('m.Time_Limit_Exceeded') }}</b> : {{ t('m.Time_Limit_Exceeded_Description') }}</li>
          <li><b>{{ t('m.Memory_Limit_Exceeded') }}</b> : {{ t('m.Memory_Limit_Exceeded_Description') }}</li>
          <li><b>{{ t('m.System_Error') }}</b> : {{ t('m.System_Error_Description') }}</li>
        </ul>
      </div>
    </Panel>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import utils from '@/utils/utils'

const { t } = useI18n()
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
