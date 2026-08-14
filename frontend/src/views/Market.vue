<template>
  <div class="page-card">
    <el-tabs v-model="activeTab" @tab-change="handleTabChange">
      <el-tab-pane label="手工行情" name="manual">
        <div class="page-header">
          <h2>市场行情记录（人工录入）</h2>
          <div class="actions">
            <el-button type="primary" @click="openDialog()">
              <el-icon><Plus /></el-icon>录入行情
            </el-button>
          </div>
        </div>

        <el-alert type="info" :closable="false" style="margin-bottom: 20px;" show-icon>
          手工录入的行情会直接进入本地市场价格记录，用于定价试算。
        </el-alert>

        <div class="search-bar">
          <el-select v-model="filterType" placeholder="行情类型" style="width: 150px;" clearable>
            <el-option label="同行报价" value="同行报价" />
            <el-option label="厂家调价" value="厂家调价" />
            <el-option label="市场涨跌" value="市场涨跌" />
            <el-option label="节日行情" value="节日行情" />
            <el-option label="淡季行情" value="淡季行情" />
          </el-select>
          <el-date-picker v-model="filterDate" type="daterange" range-separator="至"
            start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" />
          <el-button type="primary" @click="loadData">查询</el-button>
        </div>

        <el-table :data="records" stripe v-loading="loading">
          <el-table-column prop="record_date" label="记录日期" width="110" />
          <el-table-column prop="price_type" label="行情类型" width="110">
            <template #default="{ row }"><el-tag size="small">{{ row.price_type }}</el-tag></template>
          </el-table-column>
          <el-table-column prop="product_name" label="关联商品" min-width="150" />
          <el-table-column prop="competitor_price" label="同行报价" width="100">
            <template #default="{ row }"><span v-if="row.competitor_price">¥{{ row.competitor_price }}</span><span v-else>-</span></template>
          </el-table-column>
          <el-table-column prop="manufacturer_price" label="厂家报价" width="100">
            <template #default="{ row }"><span v-if="row.manufacturer_price">¥{{ row.manufacturer_price }}</span><span v-else>-</span></template>
          </el-table-column>
          <el-table-column prop="market_trend" label="市场趋势" width="100">
            <template #default="{ row }"><el-tag v-if="row.market_trend" :type="getTrendType(row.market_trend)" size="small">{{ row.market_trend }}</el-tag><span v-else>-</span></template>
          </el-table-column>
          <el-table-column prop="content" label="行情详情" min-width="250" show-overflow-tooltip />
          <el-table-column prop="operator" label="录入人" width="100" />
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" size="small" link @click="openDialog(row)">编辑</el-button>
              <el-button type="danger" size="small" link @click="handleDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="网络待确认" name="external">
        <div class="page-header">
          <h2>网络待确认</h2>
          <el-tooltip content="同步网络行情" placement="top">
            <el-button type="primary" circle :loading="syncing" aria-label="同步网络行情" @click="syncQuotes">
              <el-icon><Refresh /></el-icon>
            </el-button>
          </el-tooltip>
        </div>

        <el-alert type="warning" :closable="false" style="margin-bottom: 16px;" show-icon>
          网络报价仅供复核；确认后才会写入市场行情并参与定价试算。
        </el-alert>

        <div class="search-bar">
          <el-select v-model="quoteFilters.status" placeholder="状态" clearable style="width: 120px;" @change="loadExternalQuotes">
            <el-option label="待确认" value="pending" />
            <el-option label="已确认" value="accepted" />
            <el-option label="已忽略" value="dismissed" />
          </el-select>
          <el-select v-model="quoteFilters.product_id" placeholder="商品" clearable filterable style="width: 180px;" @change="loadExternalQuotes">
            <el-option v-for="product in products" :key="product.id" :label="product.name" :value="product.id" />
          </el-select>
          <el-select v-model="quoteFilters.quote_kind" placeholder="来源类别" clearable style="width: 150px;" @change="loadExternalQuotes">
            <el-option label="SKU 零售报价" value="retail_sku" />
            <el-option label="品类公开信息" value="official_category" />
          </el-select>
          <el-input v-model="quoteFilters.region" placeholder="地区" clearable style="width: 160px;" @clear="loadExternalQuotes" @keyup.enter="loadExternalQuotes" />
          <el-button @click="loadExternalQuotes">筛选</el-button>
        </div>

        <el-table :data="externalQuotes" stripe v-loading="quotesLoading" height="480">
          <el-table-column label="商品 / 品类范围" min-width="160">
            <template #default="{ row }"><div>{{ row.product_name || row.scope_label }}</div><small v-if="row.product_name && row.scope_label">{{ row.scope_label }}</small></template>
          </el-table-column>
          <el-table-column prop="region" label="地区" width="130" show-overflow-tooltip />
          <el-table-column label="来源" min-width="150" show-overflow-tooltip>
            <template #default="{ row }"><a v-if="safeSourceUrl(row.source_url)" :href="safeSourceUrl(row.source_url)" target="_blank" rel="noopener noreferrer">{{ row.source_name }}</a><span v-else>{{ row.source_name || '-' }}</span></template>
          </el-table-column>
          <el-table-column prop="source_excerpt" label="原始摘要" min-width="220" show-overflow-tooltip />
          <el-table-column label="抓取时间" width="170"><template #default="{ row }">{{ formatDate(row.fetched_at) }}</template></el-table-column>
          <el-table-column label="价格" width="100"><template #default="{ row }"><span v-if="hasPrice(row)">¥{{ row.price }}</span><span v-else></span></template></el-table-column>
          <el-table-column prop="unit" label="单位" width="90" />
          <el-table-column prop="trend" label="趋势" width="90" />
          <el-table-column label="状态" width="90"><template #default="{ row }"><el-tag size="small" :type="getQuoteStatusType(row.status)">{{ getQuoteStatusLabel(row.status) }}</el-tag></template></el-table-column>
          <el-table-column label="操作" width="96" fixed="right">
            <template #default="{ row }">
              <template v-if="row.status === 'pending'">
                <el-tooltip content="确认报价"><el-button type="success" link circle aria-label="确认报价" @click="openAcceptDialog(row)"><el-icon><Check /></el-icon></el-button></el-tooltip>
                <el-tooltip content="忽略报价"><el-button type="danger" link circle aria-label="忽略报价" @click="dismissQuote(row)"><el-icon><Close /></el-icon></el-button></el-tooltip>
              </template>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="dialogVisible" :title="editingRecord ? '编辑行情' : '录入行情'" width="600px">
      <el-form :model="form" label-width="100px">
        <el-row :gutter="20">
          <el-col :span="12"><el-form-item label="记录日期" required><el-date-picker v-model="form.record_date" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" style="width: 100%;" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="行情类型" required><el-select v-model="form.price_type" style="width: 100%;"><el-option label="同行报价" value="同行报价" /><el-option label="厂家调价" value="厂家调价" /><el-option label="市场涨跌" value="市场涨跌" /><el-option label="节日行情" value="节日行情" /><el-option label="淡季行情" value="淡季行情" /></el-select></el-form-item></el-col>
        </el-row>
        <el-form-item label="关联商品"><el-select v-model="form.product_id" placeholder="选择商品（可选）" filterable style="width: 100%;"><el-option v-for="p in products" :key="p.id" :label="p.name" :value="p.id" /></el-select></el-form-item>
        <el-row :gutter="20">
          <el-col :span="8"><el-form-item label="同行报价"><el-input-number v-model="form.competitor_price" :min="0" :precision="2" style="width: 100%;" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="厂家报价"><el-input-number v-model="form.manufacturer_price" :min="0" :precision="2" style="width: 100%;" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="市场趋势"><el-select v-model="form.market_trend" style="width: 100%;" placeholder="趋势"><el-option label="上涨" value="上涨" /><el-option label="持平" value="持平" /><el-option label="下跌" value="下跌" /></el-select></el-form-item></el-col>
        </el-row>
        <el-form-item label="行情详情"><el-input v-model="form.content" type="textarea" :rows="3" placeholder="详细描述行情情况..." /></el-form-item>
        <el-form-item label="操作人"><el-input v-model="form.operator" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" @click="handleSave">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="acceptDialogVisible" title="确认网络报价" width="560px" destroy-on-close>
      <el-form :model="acceptForm" label-width="94px">
        <el-form-item label="报价范围"><el-input :model-value="acceptingQuote?.scope_label" disabled /></el-form-item>
        <el-form-item label="目标商品" required>
          <el-input v-if="isSkuQuote" :model-value="acceptingQuote?.product_name || '原商品'" disabled />
          <el-select v-else v-model="acceptForm.product_id" placeholder="请选择商品" filterable style="width: 100%;"><el-option v-for="product in products" :key="product.id" :label="product.name" :value="product.id" /></el-select>
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="最终价格"><el-input-number v-model="acceptForm.price" :min="0" :precision="2" controls-position="right" style="width: 100%;" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="单位"><el-input v-model="acceptForm.unit" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="趋势"><el-input v-model="acceptForm.trend" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="acceptForm.remark" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="操作人"><el-input v-model="acceptForm.operator" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="acceptDialogVisible = false">取消</el-button><el-button type="primary" :loading="accepting" @click="acceptQuote">确认并写入行情</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  acceptExternalMarketQuote, createMarketPrice, deleteMarketPrice, dismissExternalMarketQuote,
  getExternalMarketQuotes, getMarketPrices, getProducts, syncExternalMarketQuotes, updateMarketPrice
} from '@/api'
import { sanitizeExternalSourceUrl } from '@/utils/externalMarket'

const activeTab = ref('manual')
const loading = ref(false)
const records = ref([])
const products = ref([])
const filterType = ref('')
const filterDate = ref([])
const dialogVisible = ref(false)
const editingRecord = ref(null)
const quotesLoading = ref(false)
const syncing = ref(false)
const externalQuotes = ref([])
const quoteFilters = reactive({ status: 'pending', product_id: null, quote_kind: '', region: '' })
const acceptDialogVisible = ref(false)
const accepting = ref(false)
const acceptingQuote = ref(null)
const acceptForm = reactive({ product_id: null, price: null, unit: '', trend: '', remark: '', operator: '' })

const today = new Date().toISOString().slice(0, 10)
const defaultForm = () => ({ record_date: today, product_id: null, price_type: '同行报价', competitor_price: 0, manufacturer_price: 0, market_trend: '持平', content: '', remark: '', operator: '' })
const form = reactive(defaultForm())
const isSkuQuote = computed(() => acceptingQuote.value?.quote_kind === 'retail_sku')

const getTrendType = (trend) => trend === '上涨' ? 'success' : trend === '下跌' ? 'danger' : 'info'
const getQuoteStatusLabel = (status) => ({ pending: '待确认', accepted: '已确认', dismissed: '已忽略' }[status] || status)
const getQuoteStatusType = (status) => ({ pending: 'warning', accepted: 'success', dismissed: 'info' }[status] || 'info')
const hasPrice = (quote) => quote.price !== null && quote.price !== undefined
const formatDate = (value) => value ? new Date(value).toLocaleString('zh-CN') : '-'
const safeSourceUrl = sanitizeExternalSourceUrl

const loadData = async () => {
  loading.value = true
  try {
    const params = {}
    if (filterType.value) params.price_type = filterType.value
    if (filterDate.value?.length === 2) [params.start_date, params.end_date] = filterDate.value
    records.value = await getMarketPrices(params)
  } finally { loading.value = false }
}

const loadProducts = async () => {
  const data = await getProducts({ page_size: 100 })
  products.value = data.items || []
}

const loadExternalQuotes = async () => {
  quotesLoading.value = true
  try {
    const params = Object.fromEntries(Object.entries(quoteFilters).filter(([, value]) => value !== '' && value !== null))
    externalQuotes.value = await getExternalMarketQuotes(params)
  } finally { quotesLoading.value = false }
}

const handleTabChange = (tab) => {
  if (tab === 'external') loadExternalQuotes()
}

const openDialog = (record = null) => {
  editingRecord.value = record
  Object.assign(form, record || defaultForm())
  dialogVisible.value = true
}

const handleSave = async () => {
  try {
    if (editingRecord.value) await updateMarketPrice(editingRecord.value.id, form)
    else await createMarketPrice(form)
    ElMessage.success(editingRecord.value ? '更新成功' : '录入成功')
    dialogVisible.value = false
    loadData()
  } catch { /* Axios interceptor shows the backend error. */ }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定删除此行情记录？', '确认', { type: 'warning' })
    await deleteMarketPrice(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch { /* Cancelled or already reported. */ }
}

const syncQuotes = async () => {
  syncing.value = true
  try {
    const run = await syncExternalMarketQuotes()
    if (run.status === 'success') ElMessage.success('网络行情同步完成，等待人工确认。')
    else if (run.status === 'partial') ElMessage.warning('网络行情已部分同步完成，请复核待确认报价。')
    else if (run.status === 'skipped') ElMessage.info('已有同步任务在运行，本次同步已跳过。')
    else ElMessage.error('网络行情同步未完成，请稍后重试。')
    await loadExternalQuotes()
  } catch (error) {
    if (error.response?.status === 503) ElMessage.warning('网络行情同步未配置，请联系服务器管理员配置后重启服务。')
    else ElMessage.error('网络行情同步失败，请稍后重试。')
  } finally { syncing.value = false }
}

const openAcceptDialog = (quote) => {
  acceptingQuote.value = quote
  Object.assign(acceptForm, { product_id: quote.product_id || null, price: quote.price, unit: quote.unit || '', trend: quote.trend || '', remark: '', operator: '' })
  acceptDialogVisible.value = true
}

const acceptQuote = async () => {
  if (!isSkuQuote.value && !acceptForm.product_id) {
    ElMessage.warning('请选择要关联的商品。')
    return
  }
  accepting.value = true
  try {
    const data = { ...acceptForm }
    if (isSkuQuote.value) delete data.product_id
    await acceptExternalMarketQuote(acceptingQuote.value.id, data)
    ElMessage.success('已确认并写入手工行情。')
    acceptDialogVisible.value = false
    await Promise.all([loadExternalQuotes(), loadData()])
  } catch { /* Axios interceptor shows the backend error. */ }
  finally { accepting.value = false }
}

const dismissQuote = async (quote) => {
  try {
    const { value } = await ElMessageBox.prompt('可选填写忽略原因。', '忽略网络报价', { confirmButtonText: '忽略', cancelButtonText: '取消', inputPlaceholder: '忽略原因（可选）' })
    await dismissExternalMarketQuote(quote.id, { remark: value || undefined })
    ElMessage.success('报价已忽略。')
    await Promise.all([loadExternalQuotes(), loadData()])
  } catch { /* Cancelled or Axios interceptor already reported the error. */ }
}

onMounted(async () => {
  await loadProducts()
  loadData()
})
</script>

<style scoped>
small { color: #909399; }
a { color: #409eff; }
</style>
