<template>
  <section class="page-card customer-history-page">
    <div class="page-header">
      <div><h2>客户销售历史</h2><p class="page-description">按客户和日期查看销售记录，并导出对应客户对账单。</p></div>
      <el-dropdown v-if="auth.hasRole('owner')" trigger="click" :disabled="!filters.customer_id" @command="downloadFile">
        <el-button :disabled="!filters.customer_id" :loading="downloading"><el-icon><Download /></el-icon>导出<el-icon class="button-suffix"><ArrowDown /></el-icon></el-button>
        <template #dropdown><el-dropdown-menu><el-dropdown-item command="sales:xlsx">销售历史 XLSX</el-dropdown-item><el-dropdown-item command="sales:pdf">销售历史 PDF</el-dropdown-item><el-dropdown-item command="sales:csv">销售历史 CSV</el-dropdown-item><el-dropdown-item divided command="statement:xlsx">客户对账单 XLSX</el-dropdown-item><el-dropdown-item command="statement:pdf">客户对账单 PDF</el-dropdown-item><el-dropdown-item command="statement:csv">客户对账单 CSV</el-dropdown-item></el-dropdown-menu></template>
      </el-dropdown>
    </div>

    <div class="search-bar customer-history-filters">
      <el-select v-model="filters.customer_id" filterable clearable placeholder="选择客户" @change="loadHistory"><el-option v-for="customer in customers" :key="customer.id" :label="customer.name" :value="customer.id" /></el-select>
      <el-date-picker v-model="filters.date_range" value-format="YYYY-MM-DD" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" clearable @change="loadHistory" />
      <el-button type="primary" :disabled="!filters.customer_id" :loading="loading" @click="loadHistory">查询</el-button>
    </div>

    <el-alert v-if="errorMessage" :title="errorMessage" type="error" :closable="false" show-icon class="state-alert" />
    <div class="table-scroll" v-loading="loading">
      <el-table v-if="orders.length" :data="orders" stripe height="500" table-layout="fixed">
        <el-table-column prop="order_no" label="单号" min-width="155" fixed="left" />
        <el-table-column label="销售日期" min-width="175"><template #default="{ row }">{{ dateTime(row.sale_date) }}</template></el-table-column>
        <el-table-column label="订单金额" min-width="120" align="right"><template #default="{ row }">{{ money(row.total_amount) }}</template></el-table-column>
        <el-table-column label="实收金额" min-width="120" align="right"><template #default="{ row }">{{ money(row.final_amount) }}</template></el-table-column>
        <el-table-column prop="payment_type" label="结算方式" min-width="120" />
        <el-table-column prop="items_count" label="明细数" min-width="95" align="right" />
        <el-table-column prop="status" label="状态" min-width="110" fixed="right"><template #default="{ row }"><el-tag :type="row.status === '已完成' ? 'success' : 'info'" effect="plain">{{ row.status }}</el-tag></template></el-table-column>
      </el-table>
      <el-empty v-else-if="!loading && !filters.customer_id" description="请选择客户后查询销售历史" />
      <el-empty v-else-if="!loading && !errorMessage" description="当前条件下没有销售记录" />
    </div>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ArrowDown, Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { downloadSalesHistory, exportCustomerStatement, getCustomerSales, getCustomers } from '@/api'
import { useAuth } from '@/stores/auth'
import { downloadBlob } from '@/utils/download'

const auth = useAuth()
const customers = ref([])
const orders = ref([])
const loading = ref(false)
const downloading = ref(false)
const errorMessage = ref('')
const filters = reactive({ customer_id: null, date_range: [] })
const statementParams = format => ({ format, ...(filters.date_range?.[0] ? { start_date: filters.date_range[0] } : {}), ...(filters.date_range?.[1] ? { end_date: filters.date_range[1] } : {}) })
const salesParams = () => ({ ...(filters.date_range?.[0] ? { start_date: filters.date_range[0] } : {}), ...(filters.date_range?.[1] ? { end_date: filters.date_range[1] } : {}) })
const money = value => `¥${(Number(value) || 0).toFixed(2)}`
const dateTime = value => value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '-'

const loadHistory = async () => {
  orders.value = []
  errorMessage.value = ''
  if (!filters.customer_id) return
  loading.value = true
  try { orders.value = await getCustomerSales(filters.customer_id, salesParams()) || [] } catch { errorMessage.value = '客户销售历史加载失败，请检查服务后重试。' } finally { loading.value = false }
}

const downloadFile = async command => {
  if (!filters.customer_id || !auth.hasRole('owner')) return
  const [target, format] = command.split(':')
  downloading.value = true
  try {
    const file = target === 'statement'
      ? await exportCustomerStatement(filters.customer_id, statementParams(format))
      : await downloadSalesHistory({ ...salesParams(), customer_id: filters.customer_id, format })
    downloadBlob(file, `${target === 'statement' ? '客户对账单' : '客户销售历史'}.${format}`)
    ElMessage.success(`${format.toUpperCase()} 文件已开始下载。`)
  } finally { downloading.value = false }
}

onMounted(async () => {
  try { customers.value = await getCustomers() || [] } catch { errorMessage.value = '客户列表加载失败，请稍后重试。' }
})
</script>

<style scoped>
.page-description { color: var(--color-muted); margin-top: 6px; }
.customer-history-filters :deep(.el-select) { width: min(260px, 100%); }
.customer-history-filters :deep(.el-date-editor) { width: min(320px, 100%); }
.state-alert { margin-bottom: 14px; }
.table-scroll { overflow-x: auto; }
.table-scroll :deep(.el-table) { min-width: 900px; }
</style>
