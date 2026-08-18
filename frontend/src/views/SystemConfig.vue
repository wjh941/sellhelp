<template>
  <section class="page-card config-page">
    <div class="page-header">
      <div><h2>配置管理</h2><p class="page-description">配置由服务端保存，修改可能影响本机运行方式和计划任务。</p></div>
      <el-button :loading="loading" @click="loadConfigs"><el-icon><Refresh /></el-icon>刷新</el-button>
    </div>

    <el-alert title="修改 standalone_mode 前请确认本机的登录使用方式；启用后会跳过登录验证。" type="warning" :closable="false" show-icon class="config-note" />
    <el-alert v-if="errorMessage" :title="errorMessage" type="error" :closable="false" show-icon class="config-note" />
    <div class="table-scroll" v-loading="loading">
      <el-table :data="configRows" stripe height="500" empty-text="暂无系统配置">
        <el-table-column prop="key" label="配置键" min-width="250" fixed="left" />
        <el-table-column prop="value" label="当前值" min-width="350" show-overflow-tooltip />
        <el-table-column label="操作" width="100" fixed="right"><template #default="{ row }"><el-button link type="primary" @click="openEdit(row)">编辑</el-button></template></el-table-column>
      </el-table>
    </div>
  </section>

  <el-dialog v-model="dialogVisible" title="编辑系统配置" width="min(580px, 94vw)" destroy-on-close>
    <el-form :model="form" label-position="top" class="config-form">
      <el-form-item label="配置键"><el-input v-model="form.key" disabled /></el-form-item>
      <el-form-item label="配置值"><el-input v-model="form.value" type="textarea" :rows="5" /></el-form-item>
      <el-form-item label="变更说明"><el-input v-model="form.description" maxlength="500" show-word-limit placeholder="记录此配置的用途或变更原因" /></el-form-item>
    </el-form>
    <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveConfig">保存配置</el-button></template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getSystemConfig, updateSystemConfig } from '@/api'

const rawConfigs = ref({})
const loading = ref(false)
const saving = ref(false)
const errorMessage = ref('')
const dialogVisible = ref(false)
const form = reactive({ key: '', value: '', description: '' })
const configRows = computed(() => Object.entries(rawConfigs.value || {}).map(([key, value]) => ({ key, value: typeof value === 'string' ? value : JSON.stringify(value) })).sort((left, right) => left.key.localeCompare(right.key)))

const loadConfigs = async () => {
  loading.value = true
  errorMessage.value = ''
  try { rawConfigs.value = await getSystemConfig() || {} } catch { errorMessage.value = '系统配置加载失败，请检查服务后重试。' } finally { loading.value = false }
}

const openEdit = row => { Object.assign(form, { key: row.key, value: row.value, description: '' }); dialogVisible.value = true }
const saveConfig = async () => {
  saving.value = true
  try { await updateSystemConfig(form.key, form.value, form.description || undefined); ElMessage.success('系统配置已保存。'); dialogVisible.value = false; await loadConfigs() } finally { saving.value = false }
}

loadConfigs()
</script>

<style scoped>
.page-description { color: var(--color-muted); margin-top: 6px; }
.config-note { margin-bottom: 14px; }
.table-scroll { overflow-x: auto; }
.table-scroll :deep(.el-table) { min-width: 650px; }
</style>
