<template>
  <el-row :gutter="18">
    <el-col :span="19">
      <Panel shadow>
        <template #title>{{ t('m.Problem_List') }}</template>
        <template #extra>
          <ul class="filter">
            <li>
              <el-dropdown @command="filterByDifficulty">
                <span class="el-dropdown-link">
                  {{ query.difficulty === '' ? t('m.Difficulty') : t('m.' + query.difficulty) }}
                  <el-icon><ArrowDown /></el-icon>
                </span>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="">{{ t('m.All') }}</el-dropdown-item>
                    <el-dropdown-item command="Low">{{ t('m.Low') }}</el-dropdown-item>
                    <el-dropdown-item command="Mid">{{ t('m.Mid') }}</el-dropdown-item>
                    <el-dropdown-item command="High">{{ t('m.High') }}</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </li>
            <li>
              <el-switch v-model="tagsVisible" @change="handleTagsVisible">
                <template #active-action><span class="switch-label">Tag</span></template>
                <template #inactive-action><span class="switch-label">Tag</span></template>
              </el-switch>
            </li>
            <li>
              <el-input v-model="query.keyword" placeholder="keyword" @keyup.enter="filterByKeyword">
                <template #suffix><el-icon><Search /></el-icon></template>
              </el-input>
            </li>
            <li>
              <el-button type="primary" :icon="RefreshIcon" @click="onReset">{{ t('m.Reset') }}</el-button>
            </li>
          </ul>
        </template>
        <el-table :data="problemList" v-loading="loadings.table" class="problem-table">
          <el-table-column v-if="statusColumnVisible" width="50" align="center">
            <template #default="{ row }">
              <template v-if="row.my_status === 0">
                <el-icon color="#19be6b" :size="16"><CircleCheck /></el-icon>
              </template>
              <template v-else-if="row.my_status !== null && row.my_status !== undefined">
                <el-icon color="#ed3f14" :size="16"><CircleClose /></el-icon>
              </template>
            </template>
          </el-table-column>
          <el-table-column label="#" width="80">
            <template #default="{ row }">
              <el-button link type="primary" @click="router.push({ name: 'problem-details', params: { problemID: row._id } })">
                {{ row._id }}
              </el-button>
            </template>
          </el-table-column>
          <el-table-column :label="t('m.Title')" width="400">
            <template #default="{ row }">
              <el-button link type="primary" class="title-btn" @click="router.push({ name: 'problem-details', params: { problemID: row._id } })">
                {{ row.title }}
              </el-button>
            </template>
          </el-table-column>
          <el-table-column :label="t('m.Level')">
            <template #default="{ row }">
              <el-tag :type="difficultyColor(row.difficulty)">{{ t('m.' + row.difficulty) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="t('m.Total')" prop="submission_number" />
          <el-table-column :label="t('m.AC_Rate')">
            <template #default="{ row }">{{ getACRate(row.accepted_number, row.submission_number) }}</template>
          </el-table-column>
          <el-table-column v-if="tagsVisible" :label="t('m.Tags')" align="center">
            <template #default="{ row }">
              <div class="tag-list">
                <el-tag v-for="tag in row.tags" :key="tag" class="tag-item">{{ tag }}</el-tag>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </Panel>
      <Pagination :total="total" :page-size="query.limit" :current="query.page"
                  @on-change="onPageChange" :show-sizer="true"
                  @on-page-size-change="onPageSizeChange" />
    </el-col>

    <el-col :span="5">
      <Panel :padding="10">
        <template #title><div class="taglist-title">{{ t('m.Tags') }}</div></template>
        <div v-loading="loadings.tag">
          <el-button v-for="tag in tagList" :key="tag.name" @click="filterByTag(tag.name)"
                     :disabled="query.tag === tag.name" round class="tag-btn">
            {{ tag.name }}
          </el-button>
          <el-button id="pick-one" @click="pickone">
            <el-icon><Switch /></el-icon>
            {{ t('m.Pick_One') }}
          </el-button>
        </div>
      </Panel>
    </el-col>
  </el-row>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { ArrowDown, Search, Refresh as RefreshIcon, Switch, CircleCheck, CircleClose } from '@element-plus/icons-vue'
import api from '@oj/api'
import utils from '@/utils/utils'
import Pagination from '@oj/components/Pagination.vue'
import { useUserStore } from '@/store/user'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const tagList = ref([])
const problemList = ref([])
const total = ref(0)
const loadings = reactive({ table: true, tag: true })
const tagsVisible = ref(false)
const statusColumnVisible = ref(false)
const query = reactive({ keyword: '', difficulty: '', tag: '', page: 1, limit: 10 })

function getACRate (ac, total) {
  return utils.getACRate(ac, total)
}

function difficultyColor (d) {
  if (d === 'Low') return 'success'
  if (d === 'Mid') return 'info'
  if (d === 'High') return 'warning'
  return 'info'
}

function init (simulate = false) {
  const q = route.query
  query.difficulty = q.difficulty || ''
  query.keyword = q.keyword || ''
  query.tag = q.tag || ''
  query.page = parseInt(q.page) || 1
  if (query.page < 1) query.page = 1
  query.limit = parseInt(q.limit) || 10
  if (!simulate) getTagList()
  getProblemList()
}

function pushRouter () {
  router.push({ name: 'problem-list', query: utils.filterEmptyValue({ ...query }) })
}

function getProblemList () {
  const offset = (query.page - 1) * query.limit
  loadings.table = true
  api.getProblemList(offset, query.limit, query).then(res => {
    loadings.table = false
    total.value = res.data.data.total
    problemList.value = res.data.data.results
    if (userStore.isAuthenticated) {
      statusColumnVisible.value = res.data.data.results.some(p => p.my_status !== undefined && p.my_status !== null)
    }
  }, () => {
    loadings.table = false
  })
}

function getTagList () {
  api.getProblemTagList().then(res => {
    tagList.value = res.data.data
    loadings.tag = false
  }, () => {
    loadings.tag = false
  })
}

function filterByTag (tagName) {
  query.tag = tagName
  query.page = 1
  pushRouter()
}

function filterByDifficulty (difficulty) {
  query.difficulty = difficulty
  query.page = 1
  pushRouter()
}

function filterByKeyword () {
  query.page = 1
  pushRouter()
}

function handleTagsVisible () {
  // tagsVisible toggled by v-model already
}

function onPageChange (newPage) {
  query.page = newPage
  pushRouter()
}

function onPageSizeChange (newSize) {
  query.limit = newSize
  query.page = 1
  pushRouter()
}

function onReset () {
  router.push({ name: 'problem-list' })
}

function pickone () {
  api.pickone().then(res => {
    ElMessage.success('Good Luck')
    router.push({ name: 'problem-details', params: { problemID: res.data.data } })
  })
}

onMounted(() => {
  init()
})

watch(() => route.fullPath, (newVal, oldVal) => {
  if (newVal !== oldVal) init(true)
})

watch(() => userStore.isAuthenticated, (newVal) => {
  if (newVal === true) init()
})
</script>

<style scoped lang="less">
  .taglist-title {
    margin-left: -10px;
    margin-bottom: -10px;
  }

  .tag-btn {
    margin-right: 5px;
    margin-bottom: 10px;
  }

  #pick-one {
    margin-top: 10px;
    margin-left: 0;
    width: 100%;
  }

  .switch-label {
    font-size: 11px;
  }

  .problem-table {
    width: 100%;
    font-size: 16px;
  }

  .title-btn {
    justify-content: flex-start;
    width: 100%;
  }

  .tag-list {
    margin: 8px 0;
  }

  .tag-item {
    margin-right: 4px;
  }
</style>
