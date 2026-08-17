<template>
  <el-row :gutter="18">
    <el-col :span="19">
      <Panel shadow>
        <template #title>문제 목록</template>
        <template #extra>
          <ul class="filter">
            <li>
              <el-dropdown @command="filterByDifficulty">
                <span class="el-dropdown-link">
                  {{ query.difficulty === '' ? '난이도' : DIFFICULTY_LABEL[query.difficulty] }}
                  <el-icon><ArrowDown /></el-icon>
                </span>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="">전체</el-dropdown-item>
                    <el-dropdown-item v-for="d in DIFFICULTY" :key="d.value" :command="d.value">
                      {{ d.label }}
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </li>
            <li>
              <el-switch v-model="tagsVisible">
                <template #active-action><span class="switch-label">태그</span></template>
                <template #inactive-action><span class="switch-label">태그</span></template>
              </el-switch>
            </li>
            <li>
              <el-input v-model="query.keyword" placeholder="검색어" @keyup.enter="filterByKeyword">
                <template #suffix><el-icon><Search /></el-icon></template>
              </el-input>
            </li>
            <li>
              <el-button type="primary" :icon="RefreshIcon" @click="onReset">초기화</el-button>
            </li>
          </ul>
        </template>
        <el-table :key="`${statusColumnVisible}-${tagsVisible}`" :data="problemList"
                  v-loading="loadings.table" class="problem-table">
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
          <el-table-column label="제목" width="400">
            <template #default="{ row }">
              <el-button link type="primary" class="title-btn" @click="router.push({ name: 'problem-details', params: { problemID: row._id } })">
                {{ row.title }}
              </el-button>
            </template>
          </el-table-column>
          <el-table-column label="난이도">
            <template #default="{ row }">
              <DifficultyTag :value="row.difficulty" />
            </template>
          </el-table-column>
          <el-table-column label="총 제출" prop="submission_number" />
          <el-table-column label="정답률">
            <template #default="{ row }">{{ getACRate(row.accepted_number, row.submission_number) }}</template>
          </el-table-column>
          <el-table-column v-if="tagsVisible" label="태그" align="center">
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
        <template #title><div class="taglist-title">태그</div></template>
        <div v-loading="loadings.tag">
          <el-button v-for="tag in tagList" :key="tag.name" @click="filterByTag(tag.name)"
                     :disabled="query.tag === tag.name" round class="tag-btn">
            {{ tag.name }}
          </el-button>
          <el-button id="pick-one" @click="pickone">
            <el-icon><Switch /></el-icon>
            선택
          </el-button>
        </div>
      </Panel>
    </el-col>
  </el-row>
</template>

<script setup>
import { ref, reactive, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowDown, Search, Refresh as RefreshIcon, Switch, CircleCheck, CircleClose } from '@element-plus/icons-vue'
import api from '@oj/api'
import utils from '@/utils/utils'
import { DIFFICULTY, DIFFICULTY_LABEL } from '@/utils/constants'
import DifficultyTag from '@oj/components/DifficultyTag.vue'
import Pagination from '@oj/components/Pagination.vue'
import { useUserStore } from '@/store/user'

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
    ElMessage.success('행운을 빕니다')
    router.push({ name: 'problem-details', params: { problemID: res.data.data } })
  })
}

onMounted(() => {
  userStore.ensureProfile()
})

watch(() => route.fullPath, (newVal, oldVal) => {
  if (newVal !== oldVal) init(true)
})

// 로그인 여부가 확정된 뒤에 한 번, 그리고 로그인/로그아웃할 때마다 다시 부른다.
// 두 값을 한 감시자에 묶어 둘이 같이 바뀌는 최초 로드에서도 한 번만 실행되게 한다.
watch(() => [userStore.profileReady, userStore.user.id], ([ready]) => {
  if (ready) init()
}, { immediate: true })
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
