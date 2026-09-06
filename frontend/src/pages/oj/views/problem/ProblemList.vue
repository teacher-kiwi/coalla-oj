<template>
  <el-row :gutter="18">
    <el-col :span="19" class="list-column">
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
            <li v-if="userStore.isAuthenticated" class="switch-filter">
              <span class="switch-label">즐겨찾기</span>
              <el-switch :model-value="query.favorite === '1'" @change="filterByFavorite" />
            </li>
            <li class="switch-filter">
              <span class="switch-label">태그</span>
              <el-switch v-model="tagsVisible" />
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
        <el-table :key="`${statusColumnVisible}-${tagsVisible}-${userStore.isAuthenticated}`" :data="problemList"
                  v-loading="loadings.table" class="problem-table">
          <el-table-column v-if="statusColumnVisible" width="50" class-name="icon-cell">
            <template #default="{ row }">
              <template v-if="row.my_status === 0">
                <el-icon color="#19be6b" :size="16"><CircleCheck /></el-icon>
              </template>
              <template v-else-if="row.my_status !== null && row.my_status !== undefined">
                <el-icon color="#ed3f14" :size="16"><CircleClose /></el-icon>
              </template>
            </template>
          </el-table-column>
          <el-table-column v-if="userStore.isAuthenticated" width="50" class-name="icon-cell">
            <template #default="{ row }">
              <FavoriteHeart :on="!!row.my_favorite" @toggle="toggleFavorite(row)" />
            </template>
          </el-table-column>
          <el-table-column label="#" width="80">
            <template #default="{ row }">
              <el-button link type="primary" @click="router.push({ name: 'problem-details', params: { problemID: row.display_id } })">
                {{ row.display_id }}
              </el-button>
            </template>
          </el-table-column>
          <el-table-column label="제목" width="400">
            <template #default="{ row }">
              <el-button link type="primary" class="title-btn" @click="router.push({ name: 'problem-details', params: { problemID: row.display_id } })">
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
        <template #title>태그</template>
        <div v-loading="loadings.tag">
          <el-button v-for="tag in tagList" :key="tag.name" @click="filterByTag(tag.name)"
                     :disabled="query.tag === tag.name" round class="tag-btn">
            {{ tag.name }}
          </el-button>
          <el-button id="pick-one" @click="pickone">
            <el-icon><Switch /></el-icon>
            랜덤 문제
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
import FavoriteHeart from '@oj/components/FavoriteHeart.vue'
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
const query = reactive({ keyword: '', difficulty: '', tag: '', favorite: '', page: 1, limit: 10 })

function getACRate (ac, total) {
  return utils.getACRate(ac, total)
}

function init (simulate = false) {
  const q = route.query
  query.difficulty = q.difficulty || ''
  query.keyword = q.keyword || ''
  query.tag = q.tag || ''
  query.favorite = q.favorite === '1' ? '1' : ''
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

// 목록 자체가 달라지므로 주소에 남긴다(새로고침·뒤로가기가 그대로 동작한다)
function filterByFavorite (on) {
  query.favorite = on ? '1' : ''
  query.page = 1
  pushRouter()
}

// 화면에서 먼저 뒤집고 서버에 알린다. 실패하면 되돌린다.
function toggleFavorite (row) {
  const next = !row.my_favorite
  row.my_favorite = next
  const request = next ? api.addProblemFavorite(row.display_id)
                       : api.removeProblemFavorite(row.display_id)
  request.then(() => {
    // 즐겨찾기만 보는 중에 뺐으면 그 줄은 목록에서 빠져야 한다
    if (!next && query.favorite === '1') getProblemList()
  }, () => {
    row.my_favorite = !next
  })
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
  // 표의 최소 폭(고정 컬럼 530px + 나머지)이 이 칸보다 넓어지면, min-width 가 auto 인
  // 탓에 칸이 표에 맞춰 벌어지고 옆의 태그 칸이 아래로 밀려난다. 0 으로 풀면 칸은
  // 제 몫만 쓰고 표가 자기 안에서 가로 스크롤을 만든다.
  // (submission/SubmissionList.vue 에 같은 설명이 있다)
  .list-column {
    min-width: 0;
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

  // 스위치 옆에 두는 이름. 예전에는 el-switch 의 action 슬롯에 넣었는데,
  // 그 자리는 지름 16px 짜리 동그란 손잡이 안이라 한글이 줄바꿈되며 튀어나왔다.
  .switch-filter {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }

  .switch-label {
    font-size: 13px;
    color: #606266;
    white-space: nowrap;
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
