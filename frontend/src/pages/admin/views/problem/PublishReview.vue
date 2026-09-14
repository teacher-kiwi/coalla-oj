<template>
  <div class="view">
    <Panel title="문제 공개 신청">
      <template #header>
        <el-button size="small" :icon="Refresh" @click="load">새로고침</el-button>
      </template>

      <p class="guide">
        교사가 만든 문제의 공개 신청입니다. 승인하면 모든 사용자의 문제 목록에 나타나고,
        그 뒤에는 교사가 수정·삭제할 수 없습니다.
        반려하면 학급 문제로 돌아가 교사가 고쳐서 다시 신청할 수 있습니다.
      </p>

      <el-table v-loading="loading" :data="problems" class="full-width">
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="detail">
              <p class="detail-title">문제 설명</p>
              <Markdown class="detail-body" :source="row.description" />

              <el-row :gutter="16">
                <el-col :span="12">
                  <p class="detail-title">입력 설명</p>
                  <Markdown class="detail-body" :source="row.input_description" />
                </el-col>
                <el-col :span="12">
                  <p class="detail-title">출력 설명</p>
                  <Markdown class="detail-body" :source="row.output_description" />
                </el-col>
              </el-row>

              <p class="detail-title">예제 ({{ row.samples.length }}개)</p>
              <el-row v-for="(sample, index) in row.samples" :key="index" :gutter="16">
                <el-col :span="12"><pre class="sample">{{ sample.input }}</pre></el-col>
                <el-col :span="12"><pre class="sample">{{ sample.output }}</pre></el-col>
              </el-row>

              <p class="detail-title">채점용 테스트 케이스 {{ row.test_case_score.length }}개</p>
              <p class="detail-note">
                내용은 파일로만 저장되어 여기서 보이지 않습니다.
                문제 목록에서 테스트 케이스를 내려받아 확인할 수 있습니다.
              </p>

              <p class="detail-title">정답 코드 확인</p>
              <p class="detail-note">
                <!-- 테스트 케이스가 잘못되면 학생이 제대로 풀어도 오답이 나온다.
                     출제자가 정답 코드로 확인해 두었는지 여기서 보고 판단한다. -->
                <template v-if="!row.solver_verified_at">
                  확인하지 않았습니다. 출제자가 정답 코드를 넣지 않았거나,
                  넣은 뒤 테스트 케이스를 고쳤습니다.
                </template>
                <span v-else :class="row.solver_passed ? 'verify-ok' : 'verify-bad'">
                  {{ row.solver_message }} ({{ localtime(row.solver_verified_at) }})
                </span>
              </p>

              <p v-if="row.hint" class="detail-title">힌트</p>
              <Markdown v-if="row.hint" class="detail-body" :source="row.hint" />
            </div>
          </template>
        </el-table-column>
        <el-table-column label="번호" prop="display_id" width="90" />
        <el-table-column label="제목" prop="title" />
        <el-table-column label="출제자" width="140">
          <template #default="{ row }">{{ row.created_by?.username || '-' }}</template>
        </el-table-column>
        <el-table-column label="난이도" width="100" align="center">
          <template #default="{ row }">
            <span :style="{ color: DIFFICULTY_COLOR[row.difficulty] }">
              {{ DIFFICULTY_LABEL[row.difficulty] }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="태그" width="200">
          <template #default="{ row }">
            <el-tag v-for="tag in row.tags" :key="tag" size="small" class="tag-item">{{ tag }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="만든 날짜" width="180">
          <template #default="{ row }">{{ localtime(row.create_time) }}</template>
        </el-table-column>
        <el-table-column fixed="right" label="처리" width="170">
          <template #default="{ row }">
            <el-button type="success" size="small" @click="review(row, true)">승인</el-button>
            <el-button type="danger" size="small" @click="review(row, false)">반려</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <span v-if="!loading">공개 신청된 문제가 없습니다.</span>
        </template>
      </el-table>
    </Panel>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Markdown from '@oj/components/Markdown.vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import api from '../../api.js'
import time from '@/utils/time'
import { DIFFICULTY_LABEL, DIFFICULTY_COLOR } from '@/utils/constants'

const loading = ref(false)
const problems = ref([])

function localtime (val) {
  return time.utcToLocal(val)
}

function load () {
  loading.value = true
  api.getPendingProblems().then(res => {
    loading.value = false
    problems.value = res.data.data
  }, () => {
    loading.value = false
  })
}

function review (row, approve) {
  const message = approve
    ? `"${row.title}" 을(를) 공개합니다. 모든 사용자의 문제 목록에 나타납니다.`
    : `"${row.title}" 을(를) 반려합니다. 출제한 교사만 볼 수 있는 상태로 돌아갑니다.`
  ElMessageBox.confirm(message, approve ? '공개 승인' : '공개 반려', {
    confirmButtonText: approve ? '승인' : '반려',
    cancelButtonText: '취소',
    type: approve ? 'success' : 'warning'
  }).then(() => {
    api.reviewProblemPublish(row.id, approve).then(() => {
      ElMessage.success(approve ? '공개했습니다' : '반려했습니다')
      load()
    }).catch(() => {})
  }).catch(() => {})
}

onMounted(load)
</script>

<style scoped lang="less">
.verify-ok {
  color: #67c23a;
}

.verify-bad {
  color: #e6a23c;
}

  .full-width {
    width: 100%;
  }

  .guide {
    font-size: 13px;
    color: #909399;
    line-height: 1.8;
    margin-bottom: 12px;
  }

  .tag-item {
    margin-right: 4px;
  }


  .detail {
    padding: 8px 20px 16px;

    &-title {
      font-weight: 600;
      margin: 14px 0 6px;
    }

    &-body {
      line-height: 1.7;
      word-break: break-word;
    }

    &-note {
      font-size: 12px;
      color: #909399;
    }
  }

  .sample {
    background: #f5f7fa;
    border-radius: 4px;
    padding: 8px 10px;
    margin: 0 0 8px;
    white-space: pre-wrap;
    word-break: break-all;
    font-size: 13px;
  }
</style>
