<template>
  <section class="page-card history-page">
    <div class="page-header">
      <div><h2>库存盘点历史</h2><p class="page-description">查看已提交的批次盘点差异，不在此页面修改库存。</p></div>
      <el-dropdown v-if="auth.hasRole('owner')" trigger="click" @command="downloadHistory">
        <el-button :loading="downloading"><el-icon><Download /></el-icon>导出<el-icon class="button-suffix"><ArrowDown /></el-icon></el-button>
        <template #dropdown><el-dropdown-menu><el-dropdown-item command="xlsx">下载 XLSX</el-dropdown-item><el-dropdown-item command="pdf">下载 PDF</el-dropdown-item><el-dropdown-item command="csv">下载 CSV</el-dropdown-item></el-dropdown-menu></template>
      </el-dropdown>
    </div>

    <div class="search-bar history-filters">
      <el-date-picker v-model="filters.take_date" value-format="YYYY-MM-DD" type="date" placeholder="盘点日期" clearable @change="loadRecords" />
      <el-select v-model="filters.product_id" clearable filterable placeholder="全部商品" @change="loadRecords"><el-option v-for="product in products" :key="product.id" :label="product.name" :value="product.id" /></el-select>
      <el-select v-model="filters.confirmed" clearable placeholder="全部状态" @change="loadRecords"><el-option label="已确认" :value="true" /><el-option label="未确认" :value="false" /></el-select>
      <el-button type="primary" :loading="loading" @click="loadRecords">查询</el-button>
    </div>

    <el-alert v-if="errorMessage" :title="errorMessage" type="error" :closable="false" show-icon class="state-alert" />
    <div class="table-scroll" v-loading="loading">
      <el-table v-if="records.length" :data="records" stripe height="500" table-layout="fixed">
        <el-table-column prop="take_date" label="盘点日期" min-width="120" fixed="left" />
        <el-table-column prop="product_name" label="商品" min-width="170" />
        <el-table-column prop="batch_no" label="批次" min-width="140"><template #default="{ row }">{{ row.batch_no || '无批次' }}</template></el-table-column>
        <el-table-column prop="system_quantity" label="系统数量" min-width="105" align="right" />
        <el-table-column prop="actual_quantity" label="实际数量" min-width="105" align="right" />
        <el-table-column label="差异" min-width="120" align="right"><template #default="{ row }"><span :class="differenceClass(row.diff_quantity)">{{ signed(row.diff_quantity) }}</span></template></el-table-column>
        <el-table-column label="差异金额" min-width="120" align="right"><template #default="{ row }"><span :class="differenceClass(row.diff_amount)">{{ money(row.diff_amount) }}</span></template></el-table-column>
        <el-table-column prop="reason" label="原因" min-width="180" show-overflow-tooltip><template #default="{ row }">{{ row.reason || '-' }}</template></el-table-column>
        <el-table-column label="状态" min-width="100" fixed="right"><template #default="{ row }"><el-tag :type="row.confirmed ? 'success' : 'info'" effect="plain">{{ row.confirmed ? '已确认' : '未确认' }}</el-tag></template></el-table-column>
      </el-table>
      <el-empty v-else-if="!loading && !errorMessage" description="当前筛选条件下没有盘点记录" />
    </div>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ArrowDown, Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { downloadStockTakeHistory, getProducts, getStockTakes } from '@/api'
import { useAuth } from '@/stores/auth'
import { downloadBlob } from '@/utils/download'

const auth = useAuth()
const products = ref([])
const records = ref([])
const loading = ref(false)
const downloading = ref(false)
const errorMessage = ref('')
const filters = reactive({ take_date: '', product_id: null, confirmed: null })
const activeFilters = () => ({ ...(filters.take_date ? { take_date: filters.take_date } : {}), ...(filters.product_id ? { product_id: filters.product_id } : {}), ...(filters.confirmed === null ? {} : { confirmed: filters.confirmed }) })
const money = value => `¥${(Number(value) || 0).toFixed(2)}`
const signed = value => `${Number(value) > 0 ? '+' : ''}${Number(value || 0)}`
const differenceClass = value => Number(value) > 0 ? 'positive' : Number(value) < 0 ? 'negative' : ''

const loadRecords = async () => {
  loading.value = true
  errorMessage.value = ''
  try { records.value = await getStockTakes(activeFilters()) || [] } catch { errorMessage.value = '盘点历史加载失败，请检查服务后重试。' } finally { loading.value = false }
}

const downloadHistory = async format => {
  if (!auth.hasRole('owner')) return
  downloading.value = true
  try { downloadBlob(await downloadStockTakeHistory({ ...activeFilters(), format }), `库存盘点历史.${format}`); ElMessage.success(`${format.toUpperCase()} 文件已开始下载。`) } finally { downloading.value = false }
}

onMounted(async () => {
  try { products.value = (await getProducts({ page_size: 100 })).items || [] } catch { errorMessage.value = '商品列表加载失败，请稍后重试。' }
  await loadRecords()
})
</script>

<style scoped>
.page-description { color: var(--color-muted); margin-top: 6px; }
.history-filters :deep(.el-select), .history-filters :deep(.el-date-editor) { width: min(220px, 100%); }
.state-alert { margin-bottom: 14px; }
.table-scroll { overflow-x: auto; }
.table-scroll :deep(.el-table) { min-width: 1050px; }
.positive { color: var(--color-success); font-weight: 700; }
.negative { color: var(--color-danger); font-weight: 700; }
</style>
