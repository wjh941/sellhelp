<template>
  <div class="reports-page">
    <section class="page-card report-toolbar">
      <div class="page-header">
        <div>
          <h2>周度经营报表</h2>
          <p class="page-subtitle">使用已生成周报查看销售、库存和风险，不会在本页虚构业务数据。</p>
        </div>
        <div class="toolbar-actions">
          <el-select v-model="selectedWeek" aria-label="选择生成周期"><el-option v-for="week in weekOptions" :key="week" :label="week" :value="week" /></el-select>
          <el-button type="primary" size="large" :loading="generating" @click="generateReport"><el-icon><Refresh /></el-icon>{{ report ? '重新生成周报' : '生成周报' }}</el-button>
          <el-button :disabled="!report" @click="exportReport"><el-icon><Download /></el-icon>导出数据</el-button>
          <el-button type="warning" :disabled="!report" @click="printReport"><el-icon><Printer /></el-icon>打印 / 导出 PDF</el-button>
        </div>
      </div>
      <el-alert v-if="requestError" type="error" :title="requestError" show-icon :closable="false" />
    </section>

    <section v-if="loading" class="page-card loading-state"><el-skeleton :rows="7" animated /></section>
    <section v-else-if="!report" class="page-card empty-state"><el-empty description="暂无可预览的周报"><el-button type="primary" size="large" :loading="generating" @click="generateReport">生成本周周报</el-button></el-empty></section>

    <template v-else>
      <section class="report-print-area">
        <header class="report-cover">
          <div><span class="report-kicker">经营周报</span><h1>{{ report.week_start }} 至 {{ report.week_end }}</h1><p>生成时间：{{ formatDate(report.created_at) }}</p></div>
          <el-tag type="primary" effect="light">数据来自已生成周报</el-tag>
        </header>
        <div class="stat-grid">
          <article class="stat-card sales"><span>本周销售额</span><strong>{{ formatMoney(report.total_sales) }}</strong></article>
          <article class="stat-card profit"><span>本周利润</span><strong>{{ formatMoney(report.total_profit) }}</strong></article>
          <article class="stat-card orders"><span>订单数</span><strong>{{ report.order_count || 0 }}</strong></article>
          <article class="stat-card stock"><span>库存总值</span><strong>{{ formatMoney(report.stock_value) }}</strong></article>
        </div>
      </section>

      <section class="page-card report-filter-panel">
        <div class="section-heading"><div><h3>本地筛选</h3><p>点击品类或输入商品名称，仅过滤当前已加载周报。</p></div></div>
        <div class="report-filters">
          <el-select v-model="selectedCategory" clearable placeholder="全部品类"><el-option v-for="category in categories" :key="category" :label="category" :value="category" /></el-select>
          <el-input v-model="productKeyword" clearable placeholder="按商品名称筛选" />
          <el-button text type="primary" @click="clearFilters">清空筛选</el-button>
        </div>
        <el-alert v-if="categoryMapWarning" type="warning" :title="categoryMapWarning" show-icon :closable="false" class="category-map-warning" />
        <div v-if="categories.length" class="category-chips"><el-button v-for="category in categories" :key="category" :type="selectedCategory === category ? 'primary' : 'default'" size="small" @click="selectedCategory = selectedCategory === category ? '' : category">{{ category }}</el-button></div>
      </section>

      <section class="report-two-column">
        <article class="page-card report-section">
          <div class="section-heading"><div><h3>热销商品</h3><p>点击条目可按其品类筛选下方报表。</p></div><el-button text @click="toggleSection('hot')">{{ collapsed.hot ? '展开' : '收起' }}</el-button></div>
          <template v-if="!collapsed.hot">
            <el-empty v-if="!filteredHotProducts.length" description="当前筛选下暂无热销商品" :image-size="68" />
            <div v-else class="mini-bars">
              <el-tooltip v-for="row in filteredHotProducts.slice(0, 6)" :key="`${row.product_name}-${row.total_amount}`" :content="`${row.product_name}：销售额 ${formatMoney(row.total_amount)}，销量 ${row.total_qty || 0}`" placement="top">
                <button class="mini-bar" type="button" @click="selectRowCategory(row)"><span>{{ row.product_name || '未命名商品' }}</span><i><b :style="{ width: barWidth(row.total_amount, filteredHotProducts) }"></b></i><strong>{{ formatMoney(row.total_amount) }}</strong></button>
              </el-tooltip>
            </div>
            <div class="table-scroll"><el-table :data="filteredHotProducts" stripe max-height="340"><el-table-column prop="product_name" label="商品" min-width="150" /><el-table-column :formatter="categoryLabel" label="品类" min-width="110" /><el-table-column label="销售额" width="118"><template #default="{ row }">{{ formatMoney(row.total_amount) }}</template></el-table-column><el-table-column prop="total_qty" label="销量" width="90" /></el-table></div>
          </template>
        </article>
        <article class="page-card report-section">
          <div class="section-heading"><div><h3>高利润商品</h3><p>悬浮查看利润和利润率。</p></div><el-button text @click="toggleSection('profit')">{{ collapsed.profit ? '展开' : '收起' }}</el-button></div>
          <template v-if="!collapsed.profit">
            <el-empty v-if="!filteredProfitableProducts.length" description="当前筛选下暂无高利润商品" :image-size="68" />
            <div v-else class="table-scroll"><el-table :data="filteredProfitableProducts" stripe max-height="380"><el-table-column prop="product_name" label="商品" min-width="150" /><el-table-column :formatter="categoryLabel" label="品类" min-width="110" /><el-table-column label="利润" width="118"><template #default="{ row }"><span class="profit-text">{{ formatMoney(row.total_profit) }}</span></template></el-table-column><el-table-column label="利润率" width="100"><template #default="{ row }"><el-tooltip :content="`利润率 ${formatPercent(row.profit_margin)}`"><el-tag :type="marginTagType(row.profit_margin)" size="small">{{ formatPercent(row.profit_margin) }}</el-tag></el-tooltip></template></el-table-column></el-table></div>
          </template>
        </article>
      </section>

      <section class="report-two-column">
        <article class="page-card report-section">
          <div class="section-heading"><div><h3>滞销商品</h3><p>30 天无销量的库存占用。</p></div><el-button text @click="toggleSection('slow')">{{ collapsed.slow ? '展开' : '收起' }}</el-button></div>
          <template v-if="!collapsed.slow"><el-empty v-if="!filteredSlowProducts.length" description="当前筛选下暂无滞销商品" :image-size="68" /><div v-else class="table-scroll"><el-table :data="filteredSlowProducts" stripe max-height="330"><el-table-column prop="product_name" label="商品" min-width="150" /><el-table-column :formatter="categoryLabel" label="品类" min-width="110" /><el-table-column prop="current_stock" label="库存" width="90" /><el-table-column label="库存价值" width="118"><template #default="{ row }"><span class="risk-text">{{ formatMoney(row.stock_value) }}</span></template></el-table-column><el-table-column prop="days_no_sales" label="未销天数" width="100" /></el-table></div></template>
        </article>
        <article class="page-card report-section">
          <div class="section-heading"><div><h3>风险预警</h3><p>临期、积压与欠款均以颜色和状态标签提示。</p></div><el-button text @click="toggleSection('risk')">{{ collapsed.risk ? '展开' : '收起' }}</el-button></div>
          <template v-if="!collapsed.risk"><el-empty v-if="!riskItems.length" description="当前周报暂无风险项" :image-size="68" /><div v-else class="table-scroll"><el-table :data="riskItems" stripe max-height="330"><el-table-column label="风险" width="110"><template #default="{ row }"><el-tag :type="riskTagType(row.type)" size="small">{{ row.type }}</el-tag></template></el-table-column><el-table-column prop="name" label="对象" min-width="140" /><el-table-column prop="detail" label="说明" min-width="190" show-overflow-tooltip /></el-table></div></template>
        </article>
      </section>

      <section class="report-two-column report-print-area">
        <article class="page-card report-section"><div class="section-heading"><div><h3>下周经营建议</h3></div><el-button text @click="toggleSection('suggestions')">{{ collapsed.suggestions ? '展开' : '收起' }}</el-button></div><p v-if="!collapsed.suggestions" class="advice-text">{{ report.suggestions || '本周报未提供经营建议。' }}</p></article>
        <article class="page-card report-section"><div class="section-heading"><div><h3>生意顾问摘要</h3></div><el-button text @click="toggleSection('advice')">{{ collapsed.advice ? '展开' : '收起' }}</el-button></div><p v-if="!collapsed.advice" class="advice-text">{{ report.ai_business_advice || '本周报未提供顾问摘要。' }}</p></article>
      </section>
    </template>

    <section v-if="historyReports.length" class="page-card screen-only">
      <div class="section-heading"><div><h3>历史周报</h3><p>打开历史周报不会重新生成数据。</p></div></div>
      <div class="table-scroll"><el-table :data="historyReports" stripe v-loading="historyLoading"><el-table-column prop="week_start" label="周开始" width="112" /><el-table-column prop="week_end" label="周结束" width="112" /><el-table-column label="销售额" width="118"><template #default="{ row }">{{ formatMoney(row.total_sales) }}</template></el-table-column><el-table-column label="利润" width="118"><template #default="{ row }">{{ formatMoney(row.total_profit) }}</template></el-table-column><el-table-column prop="order_count" label="订单数" width="90" /><el-table-column label="操作" width="100" fixed="right"><template #default="{ row }"><el-button link type="primary" @click="viewReport(row)">查看</el-button></template></el-table-column></el-table></div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { generateReport as generateReportApi, getLatestReport, getProducts, getReport, getReports } from '@/api'

const report = ref(null)
const historyReports = ref([])
const loading = ref(false)
const historyLoading = ref(false)
const generating = ref(false)
const requestError = ref('')
const selectedWeek = ref('本周')
const weekOptions = ['本周', '上周', '两周前']
const selectedCategory = ref('')
const productKeyword = ref('')
const productCategories = ref(new Map())
const categoryMapWarning = ref('')
const productPageSize = 100
const maxProductPages = 100
const collapsed = reactive({ hot: false, profit: false, slow: false, risk: false, suggestions: false, advice: false })

const parseItems = value => {
  if (Array.isArray(value)) return value
  if (!value) return []
  try { const parsed = JSON.parse(value); return Array.isArray(parsed) ? parsed : [] } catch { return [] }
}
const hotProducts = computed(() => parseItems(report.value?.hot_products))
const profitableProducts = computed(() => parseItems(report.value?.profitable_products))
const slowProducts = computed(() => parseItems(report.value?.slow_products))
const overstockItems = computed(() => parseItems(report.value?.overstock_risk))
const expiredWarnings = computed(() => parseItems(report.value?.expired_warning))
const customerDebts = computed(() => parseItems(report.value?.customer_debts))
const itemCategory = row => productCategories.value.get(String(row.product_id)) || ''
const categories = computed(() => [...new Set([...hotProducts.value, ...profitableProducts.value, ...slowProducts.value].map(itemCategory))].filter(Boolean))
const filterProducts = items => items.filter(row => (!selectedCategory.value || itemCategory(row) === selectedCategory.value) && (!productKeyword.value.trim() || String(row.product_name || '').includes(productKeyword.value.trim())))
const filteredHotProducts = computed(() => filterProducts(hotProducts.value))
const filteredProfitableProducts = computed(() => filterProducts(profitableProducts.value))
const filteredSlowProducts = computed(() => filterProducts(slowProducts.value))
const riskItems = computed(() => [
  ...expiredWarnings.value.map(item => ({ type: '临期', name: item.product_name || '未命名商品', detail: `剩余 ${item.remaining_quantity ?? '-'}，${item.days_to_expiry ?? '-'} 天到期` })),
  ...overstockItems.value.map(item => ({ type: '积压', name: item.product_name || '未命名商品', detail: `库存价值 ${formatMoney(item.stock_value)}` })),
  ...customerDebts.value.map(item => ({ type: '欠款', name: item.customer_name || item.name || '未命名客户', detail: `欠款 ${formatMoney(item.current_debt ?? item.debt ?? item.amount)}` })),
])

const formatMoney = value => `¥${(Number(value) || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
const formatDate = value => value ? new Date(value).toLocaleString('zh-CN') : '-'
const formatPercent = value => `${(Number(value) || 0).toFixed(1)}%`
const categoryLabel = row => itemCategory(row) || '-'
const marginTagType = value => Number(value) >= 20 ? 'success' : Number(value) >= 10 ? 'warning' : 'danger'
const riskTagType = type => type === '临期' ? 'warning' : type === '欠款' ? 'danger' : 'info'
const barWidth = (value, items) => { const max = Math.max(...items.map(row => Number(row.total_amount) || 0), 1); return `${Math.max(8, Number(value || 0) / max * 100)}%` }
const clearFilters = () => { selectedCategory.value = ''; productKeyword.value = '' }
const selectRowCategory = row => {
  const category = itemCategory(row)
  if (category) selectedCategory.value = category
}
const toggleSection = section => { collapsed[section] = !collapsed[section] }

const loadLatest = async () => {
  loading.value = true
  requestError.value = ''
  try { report.value = await getLatestReport() } catch (error) { if (error.response?.status !== 404) requestError.value = '周报加载失败，请稍后重试。' } finally { loading.value = false }
}
const loadHistory = async () => {
  historyLoading.value = true
  try { historyReports.value = await getReports({ limit: 20 }) } catch { requestError.value = '历史周报加载失败，请稍后重试。' } finally { historyLoading.value = false }
}
const loadReportProducts = async () => {
  categoryMapWarning.value = ''
  try {
    const loadedProducts = []
    let page = 1
    let total = Infinity

    while (page <= maxProductPages) {
      const data = await getProducts({ page, page_size: productPageSize })
      const items = data.items || []
      loadedProducts.push(...items)
      if (Number.isFinite(Number(data.total))) total = Number(data.total)
      if (!items.length) break
      if (loadedProducts.length >= total) break
      page += 1
    }

    productCategories.value = new Map(loadedProducts
      .filter(product => product.category_name)
      .map(product => [String(product.id), product.category_name]))
    if (page > maxProductPages && loadedProducts.length < total) {
      categoryMapWarning.value = '商品分类映射达到加载上限，品类筛选可能不完整；当前周报数据不受影响。'
    }
  } catch {
    productCategories.value = new Map()
  }
}
const generateReport = async () => {
  generating.value = true
  requestError.value = ''
  try {
    const endDate = new Date()
    if (selectedWeek.value === '上周') endDate.setDate(endDate.getDate() - 7)
    if (selectedWeek.value === '两周前') endDate.setDate(endDate.getDate() - 14)
    report.value = await generateReportApi({ end_date: endDate.toLocaleDateString('en-CA') })
    ElMessage.success('周报已生成。')
    await loadHistory()
  } catch { requestError.value = '周报生成失败，请稍后重试。' } finally { generating.value = false }
}
const viewReport = async row => {
  loading.value = true
  requestError.value = ''
  try { report.value = await getReport(row.id); clearFilters() } catch { requestError.value = '历史周报加载失败，请稍后重试。' } finally { loading.value = false }
}
const exportReport = () => {
  if (!report.value) return
  const rows = [
    ['周报区间', `${report.value.week_start} 至 ${report.value.week_end}`],
    ['本周销售额', report.value.total_sales], ['本周利润', report.value.total_profit], ['订单数', report.value.order_count], ['库存总值', report.value.stock_value],
    [], ['热销商品', '销售额', '销量'], ...filteredHotProducts.value.map(row => [row.product_name, row.total_amount, row.total_qty]),
  ]
  const csv = `\uFEFF${rows.map(row => row.map(serializeCsvCell).join(',')).join('\n')}`
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = url
  link.download = `周度经营报表-${report.value.week_end || '未命名'}.csv`
  link.click()
  URL.revokeObjectURL(url)
}
const serializeCsvCell = value => {
  const escaped = String(value ?? '').replaceAll('"', '""')
  const leadingWhitespace = escaped.match(/^\s*/)?.[0] || ''
  const content = escaped.slice(leadingWhitespace.length)
  const guarded = /^[=+\-@]/.test(content) ? `${leadingWhitespace}'${content}` : escaped
  return `"${guarded}"`
}
const printReport = () => window.print()

onMounted(async () => { await Promise.all([loadLatest(), loadHistory(), loadReportProducts()]) })
</script>

<style scoped>
.reports-page { display: grid; gap: 20px; }.page-subtitle, .section-heading p { color: var(--color-muted); font-size: 14px; margin-top: 6px; }.toolbar-actions { align-items: center; display: flex; flex-wrap: wrap; gap: 10px; }.toolbar-actions :deep(.el-select) { width: 126px; }.toolbar-actions :deep(.el-input__wrapper), .toolbar-actions :deep(.el-select__wrapper) { min-height: 42px; }.loading-state, .empty-state { min-height: 300px; }.report-cover { align-items: flex-start; background: color-mix(in srgb, var(--color-primary) 5%, var(--color-surface)); border: 1px solid var(--color-border); border-radius: 8px; display: flex; justify-content: space-between; margin-bottom: 16px; padding: 22px; }.report-kicker { color: var(--color-primary); font-size: 14px; font-weight: 600; }.report-cover h1 { font-size: 22px; margin: 8px 0; }.report-cover p { color: var(--color-muted); font-size: 14px; }.stat-grid { display: grid; gap: 14px; grid-template-columns: repeat(4, minmax(0, 1fr)); }.stat-card { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 8px; min-height: 116px; padding: 18px; }.stat-card span { color: var(--color-muted); font-size: 14px; }.stat-card strong { display: block; font-size: 25px; margin-top: 15px; }.stat-card.sales { background: color-mix(in srgb, var(--color-primary) 6%, var(--color-surface)); }.stat-card.profit { background: color-mix(in srgb, var(--color-success) 6%, var(--color-surface)); }.stat-card.orders { background: color-mix(in srgb, var(--color-warning) 7%, var(--color-surface)); }.stat-card.stock { background: color-mix(in srgb, #7B61FF 6%, var(--color-surface)); }.section-heading { align-items: flex-start; display: flex; justify-content: space-between; margin-bottom: 16px; }.section-heading h3 { font-size: 17px; }.report-filters { display: flex; flex-wrap: wrap; gap: 10px; }.report-filters :deep(.el-select), .report-filters :deep(.el-input) { width: 210px; }.report-filters :deep(.el-input__wrapper), .report-filters :deep(.el-select__wrapper) { min-height: 42px; }.category-chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }.report-two-column { display: grid; gap: 20px; grid-template-columns: repeat(2, minmax(0, 1fr)); }.report-section { margin: 0; }.table-scroll { overflow-x: auto; }.table-scroll :deep(.el-table) { min-width: 560px; }.mini-bars { display: grid; gap: 10px; margin-bottom: 16px; }.mini-bar { align-items: center; background: transparent; border: 0; color: var(--color-text); cursor: pointer; display: grid; font: inherit; gap: 10px; grid-template-columns: minmax(100px, 1fr) minmax(100px, 1.8fr) auto; padding: 4px 0; text-align: left; width: 100%; }.mini-bar:hover span { color: var(--color-primary); }.mini-bar i { background: var(--el-fill-color); border-radius: 3px; height: 10px; overflow: hidden; }.mini-bar b { background: var(--color-primary); border-radius: inherit; display: block; height: 100%; }.mini-bar strong { font-size: 14px; }.profit-text { color: var(--color-success); font-weight: 600; }.risk-text { color: var(--color-danger); font-weight: 600; }.advice-text { line-height: 1.85; min-height: 90px; white-space: pre-wrap; }
@media (max-width: 980px) { .stat-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }.report-two-column { grid-template-columns: 1fr; } }.report-cover { gap: 12px; }.toolbar-actions { justify-content: flex-start; }
@media print { .report-toolbar, .report-filter-panel, .toolbar-actions, .screen-only { display: none !important; }.reports-page { display: block; }.report-print-area, .report-section { break-inside: avoid; }.report-cover, .stat-card, .page-card { box-shadow: none; }.report-two-column { display: grid; grid-template-columns: 1fr 1fr; } }
</style>
