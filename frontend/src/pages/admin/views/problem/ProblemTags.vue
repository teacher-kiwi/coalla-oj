<template>
  <div class="view problem-tags">
    <Panel title="Problem Tags">
      <template #header>
        <el-input v-model="keyword" :prefix-icon="SearchIcon" placeholder="Keywords" />
      </template>
      <el-table v-loading="loading" :data="tagList" class="full-width">
        <el-table-column width="100" prop="id" label="ID" />
        <el-table-column prop="name" label="Tag Name" />
        <el-table-column label="Aliases">
          <template #default="{ row }">
            <el-tag v-for="alias in row.aliases" :key="alias" class="alias-tag">{{ alias }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column fixed="right" label="Operation" width="160">
          <template #default="{ row }">
            <icon-btn name="Edit" icon="Edit" @click="openTagDialog(row)" />
            <icon-btn name="Delete" icon="Delete" @click="deleteTag(row.id)" />
          </template>
        </el-table-column>
      </el-table>
      <div class="panel-options">
        <el-button type="primary" size="small" @click="openTagDialog(null)" :icon="Plus">
          Create
        </el-button>
        <el-pagination class="page" layout="prev, pager, next"
                       @current-change="currentChange" :page-size="pageSize" :total="total" />
      </div>
    </Panel>

    <el-dialog :title="dialogTitle" v-model="dialogVisible" :close-on-click-modal="false" width="420px">
      <el-form label-position="top">
        <el-form-item label="Tag Name" required>
          <el-input v-model="tagName" placeholder="Tag Name" @keyup.enter="submitTag" />
        </el-form-item>
        <el-form-item label="Aliases">
          <el-select v-model="tagAliases" multiple filterable allow-create default-first-option
                     placeholder="Aliases" class="full-width">
            <el-option v-for="alias in tagAliases" :key="alias" :label="alias" :value="alias" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <cancel @click="dialogVisible = false" />
        <save @click="submitTag" />
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search as SearchIcon } from '@element-plus/icons-vue'
import api from '../../api.js'

const pageSize = 15
const total = ref(0)
const currentPage = ref(1)
const keyword = ref('')
const loading = ref(false)
const tagList = ref([])
const dialogVisible = ref(false)
const dialogTitle = ref('')
const mode = ref('create')
const currentTagId = ref(null)
const tagName = ref('')
const tagAliases = ref([])

function getTags (page = 1) {
  loading.value = true
  api.getAdminProblemTagList({
    paging: true,
    offset: (page - 1) * pageSize,
    limit: pageSize,
    keyword: keyword.value
  }).then(res => {
    loading.value = false
    total.value = res.data.data.total
    tagList.value = res.data.data.results
  }, () => {
    loading.value = false
  })
}

function currentChange (page) {
  currentPage.value = page
  getTags(page)
}

function openTagDialog (tag) {
  if (tag) {
    mode.value = 'edit'
    currentTagId.value = tag.id
    tagName.value = tag.name
    tagAliases.value = [...(tag.aliases || [])]
    dialogTitle.value = 'Edit Tag'
  } else {
    mode.value = 'create'
    currentTagId.value = null
    tagName.value = ''
    tagAliases.value = []
    dialogTitle.value = 'Create Tag'
  }
  dialogVisible.value = true
}

function submitTag () {
  const name = tagName.value.trim()
  if (!name) {
    ElMessage.error('Tag name is required')
    return
  }
  const aliases = tagAliases.value.map(alias => alias.trim()).filter(alias => alias)
  const request = mode.value === 'edit'
    ? api.editProblemTag({ id: currentTagId.value, name, aliases })
    : api.createProblemTag({ name, aliases })
  request.then(() => {
    dialogVisible.value = false
    getTags(currentPage.value)
  }).catch(() => {})
}

function deleteTag (id) {
  ElMessageBox.confirm('Are you sure you want to delete this tag?', 'Delete Tag', {
    confirmButtonText: 'Delete',
    cancelButtonText: 'Cancel',
    type: 'warning'
  }).then(() => {
    api.deleteProblemTag(id).then(() => getTags(currentPage.value)).catch(() => {})
  }).catch(() => {})
}

onMounted(() => getTags())
watch(keyword, () => currentChange(1))
</script>

<style scoped>
.full-width {
  width: 100%;
}

.alias-tag {
  margin-right: 4px;
}
</style>
