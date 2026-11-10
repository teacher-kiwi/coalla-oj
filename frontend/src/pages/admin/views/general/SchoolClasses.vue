<template>
  <div class="view">
    <Panel title="수업">
      <template #header>
        <div class="filters">
          <el-select v-model="teacherId" placeholder="모든 선생님" clearable filterable class="teacher-select">
            <el-option v-for="t in teachers" :key="t.id" :value="t.id"
                       :label="`${t.username} (${t.class_count})`" />
          </el-select>
          <el-radio-group v-model="archived">
            <el-radio-button value="">전체</el-radio-button>
            <el-radio-button value="false">활성</el-radio-button>
            <el-radio-button value="true">비활성</el-radio-button>
          </el-radio-group>
          <el-input v-model="keyword" :prefix-icon="SearchIcon" placeholder="학교·선생님 검색" clearable
                    class="keyword" />
        </div>
      </template>
      <p class="help">
        모든 선생님의 학급입니다. 담당 선생님을 바꾸려면 사용자 화면의 '교육 데이터 정리'에서
        선생님 단위로 넘깁니다(문제집·대회 배포가 함께 옮겨 가야 해서 학급 하나만 넘기지 않습니다).
      </p>
      <el-table v-loading="loading" :data="classes" class="full-width" @row-click="openDetail">
        <el-table-column prop="school_name" label="학교" min-width="160" />
        <el-table-column prop="display_name" label="학급" min-width="170" />
        <el-table-column label="선생님" min-width="120">
          <template #default="{ row }">
            <a class="link" @click.stop="teacherId = row.teacher_id">{{ row.teacher_name }}</a>
          </template>
        </el-table-column>
        <el-table-column prop="student_count" label="학생" width="80" align="right" />
        <el-table-column label="상태" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.is_archived" size="small" type="info">비활성</el-tag>
            <el-tag v-else size="small" type="success">활성</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="만든 날" width="120">
          <template #default="{ row }">{{ localdate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column fixed="right" label="옵션" width="150">
          <template #default="{ row }">
            <span @click.stop>
              <icon-btn name="학생 보기" icon="View" @click="openDetail(row)" />
              <icon-btn name="수정" icon="Edit" @click="openEdit(row)" />
              <icon-btn name="삭제" icon="Delete" @click="removeClass(row)" />
            </span>
          </template>
        </el-table-column>
      </el-table>
      <div class="panel-options">
        <el-pagination class="page" layout="prev, pager, next, total" :current-page="currentPage"
                       @current-change="load" :page-size="pageSize" :total="total" />
      </div>
    </Panel>

    <el-dialog v-model="showDetail" width="760px" :title="detailTitle">
      <div v-loading="loadingDetail">
        <ul class="facts">
          <li>선생님 <b>{{ detail.teacher_name }}</b></li>
          <li>학생 <b>{{ detail.student_count }}</b>명</li>
          <li>배포된 문제집 <b>{{ detail.problem_set_count }}</b>개</li>
          <li>배포된 대회 <b>{{ detail.contest_count }}</b>개</li>
          <li v-if="detail.is_archived"><el-tag size="small" type="info">비활성</el-tag></li>
        </ul>
        <el-table :data="detail.students || []" max-height="420" empty-text="학생이 없습니다">
          <el-table-column prop="number" label="번호" width="70" align="right" />
          <el-table-column prop="nickname" label="이름" min-width="120" />
          <el-table-column prop="username" label="아이디" min-width="150" />
          <el-table-column prop="submission_count" label="제출" width="80" align="right" />
          <el-table-column label="마지막 로그인" width="170">
            <template #default="{ row }">
              {{ localtime(row.last_login) }}
              <el-tag v-if="row.is_disabled" size="small" type="danger">비활성</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>

    <el-dialog v-model="showEdit" title="학급 수정" width="460px" :close-on-click-modal="false">
      <el-form :model="editing" label-width="90px" label-position="left">
        <el-form-item label="학교">{{ editing.school_name }}</el-form-item>
        <el-form-item label="선생님">{{ editing.teacher_name }}</el-form-item>
        <el-form-item label="학년도">
          <el-input-number v-model="editing.year" :min="2000" :max="2100" controls-position="right" />
        </el-form-item>
        <el-form-item label="학년">
          <el-input-number v-model="editing.grade" :min="1" :max="6" controls-position="right" />
        </el-form-item>
        <el-form-item label="반">
          <el-input-number v-model="editing.class_no" :min="1" :max="99" controls-position="right" />
        </el-form-item>
        <el-form-item label="활성">
          <el-switch v-model="editing.active" />
          <span class="switch-help">끄면 학생이 로그인할 수 없습니다. 기록은 남습니다</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <cancel @click="showEdit = false" />
        <save @click="saveEdit" />
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// 최고관리자 '수업' 탭. 최고관리자는 수업을 하지 않으므로 교사 화면 대신 여기서
// 모든 선생님의 학급을 살피고 고치고 지운다.
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessageBox } from 'element-plus'
import { Search as SearchIcon } from '@element-plus/icons-vue'
import api from '../../api.js'
import time from '@/utils/time'

const pageSize = 20
const total = ref(0)
const currentPage = ref(1)
const loading = ref(false)
const classes = ref([])
const teachers = ref([])
const teacherId = ref(null)
const archived = ref('')
const keyword = ref('')

const showDetail = ref(false)
const loadingDetail = ref(false)
const detail = ref({})
const showEdit = ref(false)
const editing = ref({})

const detailTitle = computed(() =>
  detail.value.school_name ? `${detail.value.school_name} ${detail.value.display_name}` : '학급')

function localtime (val) { return val ? time.utcToLocal(val) : '-' }
function localdate (val) { return val ? time.utcToLocal(val, 'YYYY-MM-DD') : '-' }

function load (page = 1) {
  currentPage.value = page
  loading.value = true
  const params = { offset: (page - 1) * pageSize, limit: pageSize }
  if (teacherId.value) params.teacher_id = teacherId.value
  if (archived.value) params.archived = archived.value
  if (keyword.value.trim()) params.keyword = keyword.value.trim()
  api.getSchoolClassList(params).then(res => {
    const data = res.data.data
    classes.value = data.results
    total.value = data.total
    teachers.value = data.teachers
  }, () => {}).finally(() => { loading.value = false })
}

function openDetail (row) {
  detail.value = { ...row }
  showDetail.value = true
  loadingDetail.value = true
  api.getSchoolClass(row.id).then(res => {
    detail.value = res.data.data
  }, () => {}).finally(() => { loadingDetail.value = false })
}

function openEdit (row) {
  editing.value = { ...row, active: !row.is_archived }
  showEdit.value = true
}

function saveEdit () {
  const { id, year, grade, class_no: classNo, active } = editing.value
  api.editSchoolClass({ id, year, grade, class_no: classNo, is_archived: !active }).then(() => {
    showEdit.value = false
    load(currentPage.value)
  }, () => {})
}

function removeClass (row) {
  const msg = `${row.teacher_name} 선생님의 ${row.school_name} ${row.display_name}을(를) 지웁니다.\n` +
    `학생 계정 ${row.student_count}개와 그 제출 기록도 함께 지워지며 되돌릴 수 없습니다.\n` +
    '기록은 남기고 잠시 막아 두려면 지우지 말고 비활성으로 두세요.'
  ElMessageBox.confirm(msg, '학급 삭제', {
    type: 'warning', confirmButtonText: '삭제', confirmButtonClass: 'el-button--danger'
  }).then(() => {
    api.deleteSchoolClass(row.id).then(() => {
      load(classes.value.length === 1 && currentPage.value > 1 ? currentPage.value - 1 : currentPage.value)
    }, () => {})
  }, () => {})
}

// 검색어는 칠 때마다 부르지 않도록 잠깐 기다린다
let keywordTimer = null
watch(keyword, () => {
  clearTimeout(keywordTimer)
  keywordTimer = setTimeout(() => load(1), 300)
})
watch([teacherId, archived], () => load(1))

onMounted(() => load(1))
</script>

<style scoped lang="less">
.full-width { width: 100%; }
.filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
  .teacher-select { width: 200px; }
  .keyword { width: 220px; }
}
.help {
  margin: 0 0 12px;
  font-size: 12px;
  color: #909399;
}
.link {
  color: var(--el-color-primary);
  cursor: pointer;
}
:deep(.el-table__row) { cursor: pointer; }
.facts {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 20px;
  margin: 0 0 12px;
  padding: 0;
  list-style: none;
  color: #606266;
}
.switch-help {
  margin-left: 10px;
  font-size: 12px;
  color: #909399;
}
</style>
