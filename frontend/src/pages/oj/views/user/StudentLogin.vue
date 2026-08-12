<template>
  <div class="student-login">
    <!-- 1단계: 학교 찾기 -->
    <template v-if="step === 'school'">
      <p class="guide">다니는 학교를 찾아주세요.</p>
      <el-input v-model="keyword" placeholder="학교 이름 (두 글자 이상)" size="large"
                :prefix-icon="Search" @keyup.enter="searchSchool" />
      <el-button type="primary" class="btn" :loading="loading" @click="searchSchool">
        학교 찾기
      </el-button>

      <ul v-if="schools.length" class="pick-list">
        <li v-for="school in schools" :key="school.id" @click="selectSchool(school)">
          <span class="pick-name">{{ school.name }}</span>
          <span class="pick-sub">{{ school.office }}</span>
        </li>
      </ul>
      <p v-else-if="searched" class="empty">
        검색된 학교가 없습니다. 선생님께 학교가 등록되어 있는지 여쭤보세요.
      </p>
    </template>

    <!-- 2단계: 우리 반 고르기 -->
    <template v-else-if="step === 'class'">
      <p class="guide">
        <b>{{ selectedSchool.name }}</b><br />
        우리 반과 선생님을 골라주세요.
      </p>
      <ul class="pick-list">
        <li v-for="item in classes" :key="item.id" @click="selectClass(item)">
          <span class="pick-name">{{ item.grade }}학년 {{ item.class_no }}반</span>
          <span class="pick-sub">{{ item.teacher_name }} 선생님</span>
        </li>
      </ul>
      <p v-if="!classes.length" class="empty">등록된 학급이 없습니다.</p>
      <el-button link class="back" @click="goBack('school')">← 학교 다시 고르기</el-button>
    </template>

    <!-- 3단계: 번호와 비밀번호 -->
    <template v-else>
      <p class="guide">
        <b>{{ selectedSchool.name }}</b><br />
        {{ selectedClass.grade }}학년 {{ selectedClass.class_no }}반
        · {{ selectedClass.teacher_name }} 선생님
      </p>
      <el-form @submit.prevent>
        <el-form-item>
          <el-input v-model="number" type="number" placeholder="번호" size="large" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="password" type="password" inputmode="numeric" maxlength="4"
                    placeholder="비밀번호 (숫자 4자리)" size="large"
                    @keyup.enter="login" />
        </el-form-item>
      </el-form>
      <el-button type="primary" class="btn" :loading="loading" @click="login">로그인</el-button>
      <p class="hint">비밀번호를 잊었다면 선생님께 말씀드리세요.</p>
      <el-button link class="back" @click="goBack('class')">← 반 다시 고르기</el-button>
    </template>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import api from '@oj/api'
import { useAppStore } from '@/store/app'
import { useUserStore } from '@/store/user'

const appStore = useAppStore()
const userStore = useUserStore()

const step = ref('school')
const loading = ref(false)
const searched = ref(false)
const keyword = ref('')
const schools = ref([])
const classes = ref([])
const selectedSchool = ref({})
const selectedClass = ref({})
const number = ref('')
const password = ref('')

function searchSchool () {
  if (keyword.value.trim().length < 2) {
    ElMessage.error('학교 이름을 두 글자 이상 입력해주세요')
    return
  }
  loading.value = true
  api.searchStudentSchool(keyword.value.trim()).then(res => {
    loading.value = false
    searched.value = true
    schools.value = res.data.data
  }, () => {
    loading.value = false
  })
}

function selectSchool (school) {
  selectedSchool.value = school
  api.getStudentClasses(school.id).then(res => {
    classes.value = res.data.data
    step.value = 'class'
  }, () => {})
}

function selectClass (item) {
  selectedClass.value = item
  step.value = 'login'
}

function goBack (to) {
  step.value = to
}

function login () {
  if (!number.value) {
    ElMessage.error('번호를 입력해주세요')
    return
  }
  if (!/^\d{4}$/.test(password.value)) {
    ElMessage.error('비밀번호는 숫자 4자리입니다')
    return
  }
  loading.value = true
  api.studentLogin({
    school_class: selectedClass.value.id,
    number: parseInt(number.value),
    password: password.value
  }).then(() => {
    loading.value = false
    appStore.changeModalStatus({ visible: false })
    userStore.getProfile()
    ElMessage.success('환영합니다')
  }, () => {
    loading.value = false
    password.value = ''
  })
}
</script>

<style lang="less" scoped>
.student-login {
  .guide {
    font-size: 14px;
    color: #606266;
    line-height: 1.7;
    margin-bottom: 14px;
  }

  .btn {
    width: 100%;
    margin-top: 12px;
  }

  .pick-list {
    list-style: none;
    padding: 0;
    margin: 14px 0 0;
    max-height: 260px;
    overflow-y: auto;

    li {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 14px;
      border: 1px solid #dcdfe6;
      border-radius: 6px;
      margin-bottom: 8px;
      cursor: pointer;

      &:hover {
        border-color: #409eff;
        background: #ecf5ff;
      }
    }
  }

  .pick-name {
    font-size: 15px;
  }

  .pick-sub {
    font-size: 13px;
    color: #909399;
  }

  .empty,
  .hint {
    font-size: 13px;
    color: #909399;
    margin-top: 12px;
  }

  .back {
    margin-top: 10px;
  }
}
</style>
