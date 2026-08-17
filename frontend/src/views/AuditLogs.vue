<template>
  <section class="page-card audit-page">
    <div class="page-header">
      <div>
        <h2>审计日志</h2>
        <p class="page-description">敏感操作由系统自动记录，应用界面不提供修改或删除入口。</p>
      </div>
      <el-button :icon="Refresh" @click="loadData">刷新</el-button>
    </div>

    <div class="search-bar audit-filters">
      <el-select v-model="filters.operation_type" clearable placeholder="全部操作" @change="resetAndLoad">
        <el-option label="登录成功" value="login" />
        <el-option label="登录失败" value="login_failed" />
        <el-option label="权限拒绝" value="access_denied" />
        <el-option label="敏感请求" value="request" />
      </el-select>
      <el-select v-model="filters.user_id" clearable filterable placeholder="全部操作员" @change="resetAndLoad">
        <el-option v-for="user in users" :key="user.id" :label="`${user.display_name} (${user.username})`" :value="user.id" />
      </el-select>
    </div>

    <el-table v-loading="loading" :data="logs" class="data-table" empty-text="暂无审计记录">
      <el-table-column label="时间" min-width="170"><template #default="{ row }">{{ formatTime(row.timestamp) }}</template></el-table-column>
      <el-table-column prop="username" label="操作员" min-width="130"><template #default="{ row }">{{ row.username || '未关联账户' }}</template></el-table-column>
      <el-table-column prop="operation_type" label="操作类型" min-width="130"><template #default="{ row }"><el-tag :type="tagType(row.operation_type)" effect="plain">{{ operationLabel(row.operation_type) }}</el-tag></template></el-table-column>
      <el-table-column prop="operation_detail" label="操作详情" min-width="280" show-overflow-tooltip />
      <el-table-column prop="client_ip" label="客户端 IP" min-width="130" />
      <el-table-column prop="status_code" label="结果" width="90"><template #default="{ row }"><el-tag :type="row.status_code >= 400 ? 'danger' : 'success'">{{ row.status_code }}</el-tag></template></el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="total"
      :page-sizes="[20, 50, 100]"
      layout="total, sizes, prev, pager, next"
      class="audit-pagination"
      @current-change="loadData"
      @size-change="resetAndLoad"
    />
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { getAuditLogs, getUsers } from '@/api'

const loading = ref(false)
const logs = ref([])
const users = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filters = reactive({ operation_type: '', user_id: null })

const operationLabel = (type) => ({
  login: '登录成功',
  login_failed: '登录失败',
  access_denied: '权限拒绝',
  request: '敏感请求',
}[type] || type)

const tagType = type => (type === 'access_denied' || type === 'login_failed' ? 'danger' : type === 'login' ? 'success' : 'info')
const formatTime = time => new Date(time).toLocaleString('zh-CN', { hour12: false })

const loadData = async () => {
  loading.value = true
  try {
    const result = await getAuditLogs({
      page: page.value,
      page_size: pageSize.value,
      ...(filters.operation_type ? { operation_type: filters.operation_type } : {}),
      ...(filters.user_id ? { user_id: filters.user_id } : {}),
    })
    logs.value = result.items
    total.value = result.total
  } finally {
    loading.value = false
  }
}

const resetAndLoad = () => {
  page.value = 1
  loadData()
}

onMounted(async () => {
  users.value = await getUsers()
  await loadData()
})
</script>

<style lang="scss" scoped>
.page-description {
  color: var(--color-muted);
  margin-top: 6px;
}

.audit-filters :deep(.el-select) { width: min(260px, 100%); }

.audit-pagination {
  justify-content: flex-end;
  margin-top: 18px;
}

@media (max-width: 640px) {
  .audit-pagination { justify-content: flex-start; }
}
</style>
