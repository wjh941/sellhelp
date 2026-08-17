<template>
  <div class="market-page">
    <section class="page-card">
      <div class="page-header">
        <div>
          <h2>市场行情记录</h2>
          <p class="page-subtitle">人工录入与已确认网络报价，按时间倒序查看。</p>
        </div>
        <el-button type="primary" size="large" @click="openDialog()">
          <el-icon><Plus /></el-icon>录入行情
        </el-button>
      </div>

      <el-alert type="info" :closable="false" show-icon>
        手工录入的行情会直接进入本地市场价格记录，用于定价试算。
      </el-alert>

      <div class="filter-row" aria-label="行情本地筛选">
        <el-select v-model="filterType" placeholder="全部行情类型" clearable>
          <el-option label="同行报价" value="同行报价" />
          <el-option label="厂家调价" value="厂家调价" />
          <el-option label="市场涨跌" value="市场涨跌" />
          <el-option label="节日行情" value="节日行情" />
          <el-option label="淡季行情" value="淡季行情" />
        </el-select>
        <el-date-picker v-model="filterDate" type="daterange" range-separator="至"
          start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" />
        <span class="filter-hint">筛选只作用于已加载记录，不会重复请求。</span>
      </div>

      <el-alert v-if="manualError" type="error" :title="manualError" show-icon :closable="false" class="request-error" />
      <div v-loading="loading" class="timeline-wrap">
        <el-empty v-if="!loading && !filteredRecords.length" description="暂无符合条件的行情记录" :image-size="88" />
        <el-timeline v-else>
          <el-timeline-item v-for="row in filteredRecords" :key="row.id" :timestamp="row.record_date" placement="top" :type="getTrendType(row.market_trend)">
            <article class="timeline-card">
              <div class="timeline-card__topline">
                <div>
                  <strong>{{ row.product_name || '通用行情' }}</strong>
                  <el-tag size="small" effect="light">{{ row.price_type || '行情记录' }}</el-tag>
                  <el-tag v-if="row.market_trend" size="small" :type="getTrendType(row.market_trend)" effect="light">{{ row.market_trend }}</el-tag>
                </div>
                <div class="timeline-card__actions">
                  <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
                  <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
                </div>
              </div>
              <div class="price-pills">
                <span>同行报价 <b>{{ formatMoney(row.competitor_price) }}</b></span>
                <span>厂家报价 <b>{{ formatMoney(row.manufacturer_price) }}</b></span>
                <span>录入人 <b>{{ row.operator || '-' }}</b></span>
              </div>
              <el-tooltip :content="fullRemark(row) || '未填写行情详情'" placement="top-start" :show-after="350">
                <p class="timeline-card__remark">{{ expandedRecordIds.includes(row.id) ? (fullRemark(row) || '未填写行情详情') : remarkPreview(row) }}</p>
              </el-tooltip>
              <el-button v-if="fullRemark(row).length > 70" link type="primary" @click="toggleRemark(row.id)">
                {{ expandedRecordIds.includes(row.id) ? '收起详情' : '展开详情' }}
              </el-button>
            </article>
          </el-timeline-item>
        </el-timeline>
      </div>
    </section>

    <section class="page-card">
      <div class="page-header">
        <div>
          <h2>网络待确认报价</h2>
          <p class="page-subtitle">网络报价须人工复核，确认后才会写入行情记录。</p>
        </div>
        <el-tooltip content="同步网络行情" placement="top">
          <el-button type="primary" circle size="large" :loading="syncing" aria-label="同步网络行情" @click="syncQuotes">
            <el-icon><Refresh /></el-icon>
          </el-button>
        </el-tooltip>
      </div>

      <el-alert type="warning" :closable="false" show-icon>
        网络报价仅供复核；确认后才会写入市场行情并参与定价试算。
      </el-alert>
      <div class="filter-row quote-filter-row">
        <el-select v-model="quoteFilters.status" placeholder="状态" clearable @change="loadExternalQuotes">
          <el-option label="待确认" value="pending" />
          <el-option label="已确认" value="accepted" />
          <el-option label="已忽略" value="dismissed" />
        </el-select>
        <el-select v-model="quoteFilters.product_id" placeholder="商品" clearable filterable @change="loadExternalQuotes">
          <el-option v-for="product in products" :key="product.id" :label="product.name" :value="product.id" />
        </el-select>
        <el-select v-model="quoteFilters.quote_kind" placeholder="来源类别" clearable @change="loadExternalQuotes">
          <el-option label="SKU 零售报价" value="retail_sku" />
          <el-option label="品类公开信息" value="official_category" />
        </el-select>
        <el-input v-model="quoteFilters.region" placeholder="地区，回车筛选" clearable @clear="loadExternalQuotes" @keyup.enter="loadExternalQuotes" />
        <el-button @click="loadExternalQuotes">刷新列表</el-button>
      </div>
      <el-alert v-if="quoteError" type="error" :title="quoteError" show-icon :closable="false" class="request-error" />
      <div class="table-scroll">
        <el-table :data="externalQuotes" stripe v-loading="quotesLoading" empty-text="暂无网络报价">
          <el-table-column label="商品 / 品类范围" min-width="175">
            <template #default="{ row }"><div>{{ row.product_name || row.scope_label }}</div><small v-if="row.product_name && row.scope_label">{{ row.scope_label }}</small></template>
          </el-table-column>
          <el-table-column prop="region" label="地区" min-width="110" show-overflow-tooltip />
          <el-table-column label="来源" min-width="155" show-overflow-tooltip>
            <template #default="{ row }"><a v-if="safeSourceUrl(row.source_url)" :href="safeSourceUrl(row.source_url)" target="_blank" rel="noopener noreferrer">{{ row.source_name }}</a><span v-else>{{ row.source_name || '-' }}</span></template>
          </el-table-column>
          <el-table-column prop="source_excerpt" label="原始摘要" min-width="220" show-overflow-tooltip />
          <el-table-column label="抓取时间" width="170"><template #default="{ row }">{{ formatDate(row.fetched_at) }}</template></el-table-column>
          <el-table-column label="价格" width="105"><template #default="{ row }">{{ hasPrice(row) ? formatMoney(row.price) : '-' }}</template></el-table-column>
          <el-table-column prop="unit" label="单位" width="92" />
          <el-table-column prop="trend" label="趋势" width="92" />
          <el-table-column label="状态" width="100"><template #default="{ row }"><el-tag size="small" :type="getQuoteStatusType(row.status)">{{ getQuoteStatusLabel(row.status) }}</el-tag></template></el-table-column>
          <el-table-column label="操作" width="110" fixed="right">
            <template #default="{ row }">
              <template v-if="row.status === 'pending'">
                <el-tooltip content="确认报价"><el-button type="success" link circle aria-label="确认报价" @click="openAcceptDialog(row)"><el-icon><Check /></el-icon></el-button></el-tooltip>
                <el-tooltip content="忽略报价"><el-button type="danger" link circle aria-label="忽略报价" @click="dismissQuote(row)"><el-icon><Close /></el-icon></el-button></el-tooltip>
              </template>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </section>

    <el-dialog v-model="dialogVisible" :title="editingRecord ? '编辑行情' : '录入行情'" width="min(640px, 92vw)" draggable>
      <el-form :model="form" label-width="92px" class="market-form">
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="记录日期" required><el-date-picker v-model="form.record_date" type="date" value-format="YYYY-MM-DD" style="width: 100%;" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="行情类型" required><el-select v-model="form.price_type" style="width: 100%;"><el-option label="同行报价" value="同行报价" /><el-option label="厂家调价" value="厂家调价" /><el-option label="市场涨跌" value="市场涨跌" /><el-option label="节日行情" value="节日行情" /><el-option label="淡季行情" value="淡季行情" /></el-select></el-form-item></el-col>
        </el-row>
        <el-form-item label="关联商品"><el-select v-model="form.product_id" placeholder="选择商品（可选）" filterable style="width: 100%;"><el-option v-for="p in products" :key="p.id" :label="p.name" :value="p.id" /></el-select></el-form-item>
        <el-row :gutter="16">
          <el-col :span="8"><el-form-item label="同行报价"><el-input-number v-model="form.competitor_price" :min="0" :precision="2" controls-position="right" style="width: 100%;" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="厂家报价"><el-input-number v-model="form.manufacturer_price" :min="0" :precision="2" controls-position="right" style="width: 100%;" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="市场趋势"><el-select v-model="form.market_trend" style="width: 100%;"><el-option label="上涨" value="上涨" /><el-option label="持平" value="持平" /><el-option label="下跌" value="下跌" /></el-select></el-form-item></el-col>
        </el-row>
        <el-form-item label="行情详情"><el-input v-model="form.content" type="textarea" :rows="4" placeholder="详细描述行情情况..." /></el-form-item>
        <el-form-item label="操作人"><el-input v-model="form.operator" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="handleSave">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="acceptDialogVisible" title="确认网络报价" width="min(560px, 92vw)" destroy-on-close draggable>
      <el-form :model="acceptForm" label-width="94px" class="market-form">
        <el-form-item label="报价范围"><el-input :model-value="acceptingQuote?.scope_label" disabled /></el-form-item>
        <el-form-item label="目标商品" required><el-input v-if="isSkuQuote" :model-value="acceptingQuote?.product_name || '原商品'" disabled /><el-select v-else v-model="acceptForm.product_id" placeholder="请选择商品" filterable style="width: 100%;"><el-option v-for="product in products" :key="product.id" :label="product.name" :value="product.id" /></el-select></el-form-item>
        <el-row :gutter="16"><el-col :span="12"><el-form-item label="最终价格"><el-input-number v-model="acceptForm.price" :min="0" :precision="2" controls-position="right" style="width: 100%;" /></el-form-item></el-col><el-col :span="12"><el-form-item label="单位"><el-input v-model="acceptForm.unit" /></el-form-item></el-col></el-row>
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
  getExternalMarketQuotes, getMarketPrices, getProducts, syncExternalMarketQuotes, updateMarketPrice,
} from '@/api'
import { sanitizeExternalSourceUrl } from '@/utils/externalMarket'

const records = ref([])
const products = ref([])
const loading = ref(false)
const saving = ref(false)
const manualError = ref('')
const filterType = ref('')
const filterDate = ref([])
const expandedRecordIds = ref([])
const dialogVisible = ref(false)
const editingRecord = ref(null)
const quotesLoading = ref(false)
const quoteError = ref('')
const syncing = ref(false)
const externalQuotes = ref([])
const quoteFilters = reactive({ status: 'pending', product_id: null, quote_kind: '', region: '' })
const acceptDialogVisible = ref(false)
const accepting = ref(false)
const acceptingQuote = ref(null)
const acceptForm = reactive({ product_id: null, price: null, unit: '', trend: '', remark: '', operator: '' })

const today = new Date().toLocaleDateString('en-CA')
const defaultForm = () => ({ record_date: today, product_id: null, price_type: '同行报价', competitor_price: 0, manufacturer_price: 0, market_trend: '持平', content: '', remark: '', operator: '' })
const form = reactive(defaultForm())
const isSkuQuote = computed(() => acceptingQuote.value?.quote_kind === 'retail_sku')

const filteredRecords = computed(() => records.value
  .filter(row => !filterType.value || row.price_type === filterType.value)
  .filter(row => {
    if (filterDate.value?.length === 2) {
      const [start, end] = filterDate.value
      return row.record_date >= start && row.record_date <= end
    }
    return true
  })
  .slice()
  .sort((left, right) => String(right.record_date || '').localeCompare(String(left.record_date || '')) || Number(right.id || 0) - Number(left.id || 0)))

const getTrendType = trend => trend === '上涨' ? 'success' : trend === '下跌' ? 'danger' : 'info'
const getQuoteStatusLabel = status => ({ pending: '待确认', accepted: '已确认', dismissed: '已忽略' }[status] || status)
const getQuoteStatusType = status => ({ pending: 'warning', accepted: 'success', dismissed: 'info' }[status] || 'info')
const hasPrice = quote => quote.price !== null && quote.price !== undefined
const formatDate = value => value ? new Date(value).toLocaleString('zh-CN') : '-'
const formatMoney = value => Number.isFinite(Number(value)) && Number(value) > 0 ? `¥${Number(value).toFixed(2)}` : '-'
const fullRemark = row => String(row.content || row.remark || '')
const remarkPreview = row => fullRemark(row).length > 70 ? `${fullRemark(row).slice(0, 70)}...` : (fullRemark(row) || '未填写行情详情')
const safeSourceUrl = sanitizeExternalSourceUrl

const toggleRemark = id => {
  expandedRecordIds.value = expandedRecordIds.value.includes(id)
    ? expandedRecordIds.value.filter(item => item !== id)
    : [...expandedRecordIds.value, id]
}

const loadData = async () => {
  loading.value = true
  manualError.value = ''
  try { records.value = await getMarketPrices({}) } catch { manualError.value = '行情记录加载失败，请稍后重试。' } finally { loading.value = false }
}
const loadProducts = async () => {
  try {
    const data = await getProducts({ page_size: 100 })
    products.value = data.items || []
  } catch { ElMessage.error('商品列表加载失败，请刷新后重试。') }
}
const loadExternalQuotes = async () => {
  quotesLoading.value = true
  quoteError.value = ''
  try {
    const params = Object.fromEntries(Object.entries(quoteFilters).filter(([, value]) => value !== '' && value !== null))
    externalQuotes.value = await getExternalMarketQuotes(params)
  } catch { quoteError.value = '网络报价加载失败，请稍后重试。' } finally { quotesLoading.value = false }
}

const openDialog = record => { editingRecord.value = record || null; Object.assign(form, defaultForm(), record || {}); dialogVisible.value = true }
const handleSave = async () => {
  saving.value = true
  try {
    if (editingRecord.value) await updateMarketPrice(editingRecord.value.id, form)
    else await createMarketPrice(form)
    ElMessage.success(editingRecord.value ? '行情已更新' : '行情已录入')
    dialogVisible.value = false
    await loadData()
  } catch { /* Axios interceptor displays backend details. */ } finally { saving.value = false }
}
const handleDelete = async row => {
  try {
    await ElMessageBox.confirm('确定删除这条行情记录？', '确认删除', { type: 'warning' })
    await deleteMarketPrice(row.id)
    ElMessage.success('行情记录已删除')
    await loadData()
  } catch { /* Cancelled or already reported. */ }
}
const syncQuotes = async () => {
  syncing.value = true
  try {
    const run = await syncExternalMarketQuotes()
    if (run.status === 'success') ElMessage.success('网络行情同步完成，请复核待确认报价。')
    else if (run.status === 'partial') ElMessage.warning('网络行情部分同步完成，请复核待确认报价。')
    else if (run.status === 'skipped') ElMessage.info('已有同步任务在运行，本次同步已跳过。')
    else ElMessage.error('网络行情同步未完成，请稍后重试。')
    await loadExternalQuotes()
  } catch (error) {
    ElMessage.error(error.response?.status === 503 ? '网络行情同步未配置，请联系管理员。' : '网络行情同步失败，请稍后重试。')
  } finally { syncing.value = false }
}
const openAcceptDialog = quote => {
  acceptingQuote.value = quote
  Object.assign(acceptForm, { product_id: quote.product_id || null, price: quote.price, unit: quote.unit || '', trend: quote.trend || '', remark: '', operator: '' })
  acceptDialogVisible.value = true
}
const acceptQuote = async () => {
  if (!isSkuQuote.value && !acceptForm.product_id) return ElMessage.warning('请选择要关联的商品。')
  accepting.value = true
  try {
    const data = { ...acceptForm }
    if (isSkuQuote.value) delete data.product_id
    await acceptExternalMarketQuote(acceptingQuote.value.id, data)
    ElMessage.success('报价已确认并写入行情。')
    acceptDialogVisible.value = false
    await Promise.all([loadExternalQuotes(), loadData()])
  } catch { /* Axios interceptor displays backend details. */ } finally { accepting.value = false }
}
const dismissQuote = async quote => {
  try {
    const { value } = await ElMessageBox.prompt('可选填写忽略原因。', '忽略网络报价', { confirmButtonText: '忽略', cancelButtonText: '取消', inputPlaceholder: '忽略原因（可选）' })
    await dismissExternalMarketQuote(quote.id, { remark: value || undefined })
    ElMessage.success('报价已忽略。')
    await Promise.all([loadExternalQuotes(), loadData()])
  } catch { /* Cancelled or already reported. */ }
}

onMounted(async () => { await loadProducts(); await Promise.all([loadData(), loadExternalQuotes()]) })
</script>

<style scoped>
.market-page { display: grid; gap: 20px; }
.page-subtitle { color: var(--color-muted); font-size: 14px; margin-top: 6px; }
.filter-row { align-items: center; display: flex; flex-wrap: wrap; gap: 12px; margin: 18px 0; }
.filter-row > :deep(.el-select), .filter-row > :deep(.el-input) { width: 180px; }
.filter-row :deep(.el-input__wrapper), .filter-row :deep(.el-select__wrapper), .filter-row :deep(.el-range-editor.el-input__wrapper) { min-height: 42px; }
.filter-hint { color: var(--color-muted); font-size: 14px; }
.request-error { margin: 0 0 16px; }
.timeline-wrap { min-height: 126px; }
.timeline-card { background: var(--el-fill-color-light); border: 1px solid var(--color-border); border-radius: 8px; padding: 14px 16px; }
.timeline-card__topline { align-items: flex-start; display: flex; gap: 12px; justify-content: space-between; }
.timeline-card__topline strong { font-size: 16px; margin-right: 8px; }
.timeline-card__topline :deep(.el-tag) { margin-right: 6px; }
.timeline-card__actions { display: flex; flex: 0 0 auto; }
.price-pills { display: flex; flex-wrap: wrap; gap: 10px; margin: 12px 0 8px; }
.price-pills span { background: var(--color-surface); border-radius: 4px; color: var(--color-muted); padding: 6px 8px; }
.price-pills b { color: var(--color-text); font-weight: 600; margin-left: 4px; }
.timeline-card__remark { color: var(--el-text-color-regular); line-height: 1.7; white-space: pre-wrap; }
.quote-filter-row > :deep(.el-select) { width: 154px; }
.table-scroll { overflow-x: auto; }
.table-scroll :deep(.el-table) { min-width: 1080px; }
small { color: var(--color-muted); }
a { color: var(--color-primary); }
.market-form :deep(.el-input__wrapper), .market-form :deep(.el-select__wrapper), .market-form :deep(.el-textarea__inner) { min-height: 42px; }
@media (max-width: 760px) { .timeline-card__topline { align-items: stretch; flex-direction: column; } .filter-row > :deep(.el-select), .filter-row > :deep(.el-input) { width: min(100%, 300px); } }
</style>
