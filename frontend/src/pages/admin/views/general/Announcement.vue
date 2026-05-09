<template>
  <div class="announcement view">
    <Panel :title="t('m.General_Announcement')">
      <div class="list">
        <el-table v-loading="loading" :data="announcementList" class="full-width">
          <el-table-column width="100" prop="id" label="ID" />
          <el-table-column prop="title" label="Title" />
          <el-table-column prop="create_time" label="CreateTime">
            <template #default="{ row }">{{ localtime(row.create_time) }}</template>
          </el-table-column>
          <el-table-column prop="last_update_time" label="LastUpdateTime">
            <template #default="{ row }">{{ localtime(row.last_update_time) }}</template>
          </el-table-column>
          <el-table-column prop="created_by.username" label="Author" />
          <el-table-column width="100" prop="visible" label="Visible">
            <template #default="{ row }">
              <el-switch v-model="row.visible" @change="handleVisibleSwitch(row)" />
            </template>
          </el-table-column>
          <el-table-column fixed="right" label="Option" width="200">
            <template #default="{ row }">
              <icon-btn name="Edit" icon="Edit" @click="openAnnouncementDialog(row.id)" />
              <icon-btn name="Delete" icon="Delete" @click="deleteAnnouncement(row.id)" />
            </template>
          </el-table-column>
        </el-table>
        <div class="panel-options">
          <el-button type="primary" size="small" @click="openAnnouncementDialog(null)" :icon="Plus">Create</el-button>
          <el-pagination v-if="!contestID" class="page" layout="prev, pager, next"
                         @current-change="currentChange" :page-size="pageSize" :total="total" />
        </div>
      </div>
    </Panel>

    <el-dialog :title="announcementDialogTitle" v-model="showEditAnnouncementDialog" :close-on-click-modal="false">
      <el-form label-position="top">
        <el-form-item :label="t('m.Announcement_Title')" required>
          <el-input v-model="announcement.title" :placeholder="t('m.Announcement_Title')" class="title-input" />
        </el-form-item>
        <el-form-item :label="t('m.Announcement_Content')" required>
          <Simditor v-model="announcement.content" />
        </el-form-item>
        <div class="visible-box">
          <span>{{ t('m.Announcement_visible') }}</span>
          <el-switch v-model="announcement.visible" />
        </div>
      </el-form>
      <template #footer>
        <cancel @click="showEditAnnouncementDialog = false" />
        <save @click="submitAnnouncement" />
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import Simditor from '../../components/Simditor.vue'
import api from '../../api.js'
import time from '@/utils/time'

const { t } = useI18n()
const route = useRoute()

const contestID = ref('')
const showEditAnnouncementDialog = ref(false)
const announcementList = ref([])
const pageSize = 15
const total = ref(0)
const currentAnnouncementId = ref(null)
const mode = ref('create')
const announcement = reactive({ title: '', visible: true, content: '' })
const announcementDialogTitle = ref('Edit Announcement')
const loading = ref(true)
const currentPage = ref(0)

function localtime (val) {
  return time.utcToLocal(val)
}

function init () {
  contestID.value = route.params.contestId || ''
  if (contestID.value) {
    getContestAnnouncementList()
  } else {
    getAnnouncementList(1)
  }
}

function currentChange (page) {
  currentPage.value = page
  getAnnouncementList(page)
}

function getAnnouncementList (page) {
  loading.value = true
  api.getAnnouncementList((page - 1) * pageSize, pageSize).then(res => {
    loading.value = false
    total.value = res.data.data.total
    announcementList.value = res.data.data.results
  }, () => { loading.value = false })
}

function getContestAnnouncementList () {
  loading.value = true
  api.getContestAnnouncementList(contestID.value).then(res => {
    loading.value = false
    announcementList.value = res.data.data
  }).catch(() => { loading.value = false })
}

function submitAnnouncement (data) {
  let funcName = ''
  if (!data?.title) {
    data = {
      id: currentAnnouncementId.value,
      title: announcement.title,
      content: announcement.content,
      visible: announcement.visible
    }
  }
  if (contestID.value) {
    data.contest_id = contestID.value
    funcName = mode.value === 'edit' ? 'updateContestAnnouncement' : 'createContestAnnouncement'
  } else {
    funcName = mode.value === 'edit' ? 'updateAnnouncement' : 'createAnnouncement'
  }
  api[funcName](data).then(() => {
    showEditAnnouncementDialog.value = false
    init()
  }).catch(() => {})
}

function deleteAnnouncement (announcementId) {
  ElMessageBox.confirm('Are you sure you want to delete this announcement?', 'Warning', {
    confirmButtonText: 'Delete',
    cancelButtonText: 'Cancel',
    type: 'warning'
  }).then(() => {
    loading.value = true
    const funcName = contestID.value ? 'deleteContestAnnouncement' : 'deleteAnnouncement'
    api[funcName](announcementId).then(() => {
      loading.value = true
      init()
    })
  }).catch(() => { loading.value = false })
}

function openAnnouncementDialog (id) {
  showEditAnnouncementDialog.value = true
  if (id !== null) {
    currentAnnouncementId.value = id
    announcementDialogTitle.value = 'Edit Announcement'
    const item = announcementList.value.find(item => item.id === id)
    if (item) {
      announcement.title = item.title
      announcement.visible = item.visible
      announcement.content = item.content
      mode.value = 'edit'
    }
  } else {
    announcementDialogTitle.value = 'Create Announcement'
    announcement.title = ''
    announcement.visible = true
    announcement.content = ''
    mode.value = 'create'
  }
}

function handleVisibleSwitch (row) {
  mode.value = 'edit'
  submitAnnouncement({ id: row.id, title: row.title, content: row.content, visible: row.visible })
}

onMounted(() => { init() })
watch(() => route.fullPath, () => { init() })
</script>

<style lang="less" scoped>
  .title-input {
    margin-bottom: 20px;
  }
  .full-width {
    width: 100%;
  }
  .visible-box {
    margin-top: 10px;
    width: 205px;
    float: left;
  }
</style>
