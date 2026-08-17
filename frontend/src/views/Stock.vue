<template>
  <div class="stock-page">
    <section class="metric-grid" aria-label="库存概览">
      <div class="metric-card primary"><span>库存占用资金</span><strong>¥{{ formatMoney(stockSummary.total_stock_value) }}</strong></div>
      <div class="metric-card warning"><span>临期批次</span><strong>{{ expiryWarnings.length }}</strong></div>
      <div class="metric-card danger"><span>低于安全库存</span><strong>{{ lowStockAlerts.length }}</strong></div>
      <div class="metric-card success"><span>在库商品分类</span><strong>{{ Object.keys(stockSummary.by_category || {}).length }}</strong></div>
    </section>

    <section class="page-card chart-card">
      <div class="section-heading"><div><p class="eyebrow">库存结构</p><h2>分类库存价值</h2></div><el-button :loading="loading" @click="loadStockData">刷新数据</el-button></div>
      <el-alert v-if="errorMessage" type="error" :title="errorMessage" show-icon :closable="false" class="state-alert" />
      <div v-if="!loading && !Object.keys(categoryStock).length" class="chart-empty">暂无分类库存数据</div>
      <div v-else ref="categoryChartRef" class="category-chart" aria-label="分类库存价值图表" />
    </section>

    <section class="page-card">
      <div class="section-heading inventory-heading">
        <div><p class="eyebrow">按批次管理</p><h2>商品库存明细</h2></div>
        <div class="filter-actions">
          <el-select v-model="selectedCategory" clearable placeholder="全部分类"><el-option v-for="item in categoryOptions" :key="item" :label="item" :value="item" /></el-select>
          <el-input v-model="searchKeyword" clearable placeholder="搜索商品或批次" />
          <el-button type="primary" :loading="loading" @click="loadStockData">刷新</el-button>
        </div>
      </div>
      <el-alert v-if="!loading && lowStockAlerts.length" type="warning" :closable="false" show-icon class="state-alert" title="存在低库存商品，请结合安全库存列安排补货。" />
      <div class="table-scroll" v-loading="loading">
        <el-table v-if="filteredBatches.length" :data="filteredBatches" stripe height="470" table-layout="fixed">
          <el-table-column prop="product_name" label="商品" min-width="155" fixed="left" show-overflow-tooltip />
          <el-table-column prop="category" label="分类" min-width="110"><template #default="{ row }"><el-tag effect="plain">{{ row.category || '未分类' }}</el-tag></template></el-table-column>
          <el-table-column prop="batch_no" label="批次号" min-width="140" show-overflow-tooltip />
          <el-table-column label="生产日期" min-width="120"><template #default="{ row }">{{ row.production_date || '未提供' }}</template></el-table-column>
          <el-table-column label="到期日期" min-width="120"><template #default="{ row }">{{ row.expiry_date || '未设置' }}</template></el-table-column>
          <el-table-column prop="remaining" label="当前库存" min-width="105" align="right"><template #default="{ row }"><span :class="stockClass(row.remaining, row.safe_stock)">{{ row.remaining }}</span></template></el-table-column>
          <el-table-column prop="safe_stock" label="安全库存" min-width="105" align="right"><template #default="{ row }">{{ row.safe_stock ?? '未设置' }}</template></el-table-column>
          <el-table-column label="风险状态" min-width="175" fixed="right"><template #default="{ row }"><el-tag :type="batchRisk(row).type" effect="light">{{ batchRisk(row).text }}</el-tag></template></el-table-column>
        </el-table>
        <el-empty v-else-if="!loading && !errorMessage" description="暂无符合条件的库存批次" />
        <el-result v-else-if="!loading && errorMessage" icon="error" title="库存数据未能加载" sub-title="请检查服务连接后重试。"><template #extra><el-button type="primary" @click="loadStockData">重新加载</el-button></template></el-result>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { getAllStock, getCategories, getCategoriesStock, getExpiryWarnings, getLowStockAlerts, getProducts, getStockSummary } from '@/api'

const loading = ref(false)
const errorMessage = ref('')
const stockSummary = ref({})
const allStock = ref([])
const expiryWarnings = ref([])
const lowStockAlerts = ref([])
const categoryStock = ref({})
const categories = ref([])
const products = ref([])
const selectedCategory = ref('')
const searchKeyword = ref('')
const categoryChartRef = ref(null)
let categoryChart = null

const formatMoney = value => (Number(value) || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const productById = computed(() => new Map(products.value.map(product => [product.id, product])))
const categoryById = computed(() => new Map(categories.value.map(category => [category.id, category.name])))
const lowStockByProduct = computed(() => new Map(lowStockAlerts.value.map(item => [item.product_id, item.safe_stock])))
const categoryOptions = computed(() => Object.keys(categoryStock.value || {}))

const batchRows = computed(() => allStock.value.flatMap(stock => {
  const product = productById.value.get(stock.product_id) || {}
  const category = product.category_name || categoryById.value.get(product.category_id) || stock.category || '未分类'
  const safeStock = product.safe_stock ?? lowStockByProduct.value.get(stock.product_id)
  return (stock.batches || []).map(batch => ({ ...batch, product_name: stock.product_name, product_id: stock.product_id, category, safe_stock: safeStock }))
}))

const filteredBatches = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  return batchRows.value.filter(row => (!selectedCategory.value || row.category === selectedCategory.value) && (!keyword || [row.product_name, row.batch_no].some(value => String(value || '').toLowerCase().includes(keyword))))
})

function batchRisk(batch) {
  const days = batch.days_to_expiry
  if (days !== null && days !== undefined && Number(days) < 0) return { type: 'danger', text: `已过期 ${Math.abs(Number(days))} 天` }
  if (days !== null && days !== undefined && Number(days) <= 15) return { type: 'warning', text: `临期，剩余 ${days} 天` }
  if (batch.safe_stock !== null && batch.safe_stock !== undefined && Number(batch.remaining) <= Number(batch.safe_stock)) return { type: 'warning', text: '低于安全库存' }
  if (days !== null && days !== undefined && Number(days) <= 30) return { type: 'info', text: `注意到期，剩余 ${days} 天` }
  return { type: 'success', text: days === null || days === undefined ? '正常，无到期日' : '正常库存' }
}

const stockClass = (stock, safeStock) => ({ 'risk-danger-text': Number(stock) <= 0, 'risk-warning-text': safeStock !== null && safeStock !== undefined && Number(stock) <= Number(safeStock) })

function renderChart() {
  if (!categoryChartRef.value || !Object.keys(categoryStock.value).length) return
  categoryChart?.dispose()
  categoryChart = echarts.init(categoryChartRef.value)
  const data = Object.entries(categoryStock.value).map(([name, info]) => ({ name, value: Number(info.total_value) || 0 }))
  categoryChart.setOption({
    color: ['#165DFF', '#00B42A', '#FF7D00', '#7A5AF8', '#14B8A6'],
    tooltip: { trigger: 'item', valueFormatter: value => `¥${formatMoney(value)}` },
    legend: { bottom: 0, type: 'scroll' },
    series: [{ type: 'pie', radius: ['42%', '68%'], avoidLabelOverlap: true, label: { formatter: '{b}\n¥{c}' }, data }],
  })
}

async function loadStockData() {
  loading.value = true
  errorMessage.value = ''
  try {
    const [summary, stock, warnings, alerts, categoryData, categoryList, productData] = await Promise.all([
      getStockSummary(), getAllStock({}), getExpiryWarnings({ warning_days: 30 }), getLowStockAlerts(), getCategoriesStock(), getCategories(), getProducts({ page_size: 1000, is_active: true }),
    ])
    stockSummary.value = summary || {}
    allStock.value = Array.isArray(stock) ? stock : []
    expiryWarnings.value = Array.isArray(warnings) ? warnings : []
    lowStockAlerts.value = Array.isArray(alerts) ? alerts : []
    categoryStock.value = categoryData || {}
    categories.value = Array.isArray(categoryList) ? categoryList : []
    products.value = productData?.items || []
    await nextTick()
    renderChart()
  } catch (error) {
    errorMessage.value = error?.message || '库存服务暂不可用'
    allStock.value = []
  } finally {
    loading.value = false
  }
}

const onWindowResize = () => categoryChart?.resize()
onMounted(() => { loadStockData(); window.addEventListener('resize', onWindowResize) })
onBeforeUnmount(() => { window.removeEventListener('resize', onWindowResize); categoryChart?.dispose() })
</script>

<style scoped>
.stock-page { display: grid; gap: 16px; }
.metric-grid { display: grid; grid-template-columns: repeat(4, minmax(180px, 1fr)); gap: 14px; overflow-x: auto; }
.metric-card { min-width: 180px; border: 1px solid var(--el-color-primary-light-5); border-radius: 8px; background: var(--el-bg-color); padding: 16px; box-shadow: 0 3px 10px rgb(31 35 41 / 5%); }
.metric-card span, .eyebrow { margin: 0; color: var(--el-text-color-secondary); font-size: 14px; }
.metric-card strong { display: block; margin-top: 8px; color: var(--el-text-color-primary); font-size: 26px; line-height: 1.2; }
.metric-card.warning { border-color: #FFCC9F; }.metric-card.danger { border-color: #FDB5B5; }.metric-card.success { border-color: #A5E8B4; }
.section-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 16px; }.section-heading h2 { margin: 3px 0 0; font-size: 20px; }.filter-actions { display: flex; flex-wrap: wrap; gap: 10px; }.filter-actions .el-select, .filter-actions .el-input { width: 170px; }
.category-chart { height: 300px; min-width: 620px; }.chart-card { overflow-x: auto; }.chart-empty { display: grid; height: 240px; place-items: center; color: var(--el-text-color-secondary); font-size: 14px; }.state-alert { margin-bottom: 14px; }.table-scroll { min-width: 0; overflow-x: auto; }.table-scroll :deep(.el-table) { min-width: 1060px; }.risk-danger-text { color: #F53F3F; font-weight: 700; }.risk-warning-text { color: #C45200; font-weight: 700; }
@media (max-width: 960px) { .inventory-heading { align-items: flex-start; flex-direction: column; }.metric-grid { grid-template-columns: repeat(4, minmax(190px, 1fr)); } }
</style>
