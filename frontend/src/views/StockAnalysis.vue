<template>
  <div class="analysis-page">
    <el-tabs v-model="activeTab" class="analysis-tabs">
      <el-tab-pane label="滞销商品" name="slow">
        <section class="page-card">
          <div class="section-heading"><div><p class="eyebrow">周转风险</p><h2>滞销商品分析</h2></div><div class="actions"><el-select v-model="slowDays" aria-label="无销售天数"><el-option :value="7" label="7 天无销售" /><el-option :value="30" label="30 天无销售" /><el-option :value="60" label="60 天无销售" /><el-option :value="90" label="90 天无销售" /></el-select><el-button type="primary" :loading="slowLoading" @click="loadSlowProducts">分析</el-button></div></div>
          <el-alert v-if="slowError" type="error" :title="slowError" show-icon :closable="false" class="state-alert" />
          <el-empty v-else-if="!slowLoading && !slowProducts.length" description="当前条件下没有滞销商品" />
          <div v-else class="table-scroll" v-loading="slowLoading"><el-table :data="slowProducts" stripe height="460" table-layout="fixed"><el-table-column prop="product_name" label="商品名称" min-width="160" fixed="left" /><el-table-column prop="category" label="分类" min-width="110"><template #default="{ row }"><el-tag effect="plain">{{ row.category || '未分类' }}</el-tag></template></el-table-column><el-table-column prop="current_stock" label="当前库存" min-width="110" align="right" /><el-table-column prop="stock_value" label="库存价值" min-width="125" align="right"><template #default="{ row }"><span class="risk-text">¥{{ formatMoney(row.stock_value) }}</span></template></el-table-column><el-table-column prop="days_no_sales" label="无销售天数" min-width="125"><template #default="{ row }"><el-tag type="warning">{{ row.days_no_sales }} 天</el-tag></template></el-table-column><el-table-column prop="total_sales_qty" label="历史销量" min-width="110" align="right" /><el-table-column label="操作" min-width="125" fixed="right"><template #default="{ row }"><el-button link type="primary" @click="showClearSuggestion(row)">清仓建议</el-button></template></el-table-column></el-table></div>
        </section>
      </el-tab-pane>

      <el-tab-pane label="库存健康" name="analysis">
        <section class="page-card" v-loading="analysisLoading">
          <div class="section-heading"><div><p class="eyebrow">库存结构</p><h2>库存健康分析</h2></div><el-button type="primary" @click="loadOverstock">重新分析</el-button></div>
          <el-alert v-if="analysisError" type="error" :title="analysisError" show-icon :closable="false" class="state-alert" />
          <template v-else-if="hasAnalysis">
            <div class="summary-grid"><article class="health-card" :class="healthLevel"><span>库存健康评分</span><strong>{{ analysis.health_score?.score ?? '-' }}</strong><el-tag :type="healthTagType">{{ analysis.health_score?.level || '暂无评级' }}</el-tag><p>{{ analysis.health_score?.suggestion || '暂无建议' }}</p></article><article class="summary-card"><span>库存总值</span><strong>¥{{ formatMoney(analysis.total_stock_value) }}</strong></article><article class="summary-card"><span>在库商品数</span><strong>{{ analysis.product_count ?? 0 }}</strong></article><article class="summary-card warning"><span>高占用风险商品</span><strong>{{ riskSummary.length }}</strong></article></div>
            <div class="analysis-grid"><section class="subsection"><h3>分类库存摘要</h3><div v-if="categorySummary.length" ref="categoryChartRef" class="category-chart" /><div v-else class="chart-empty">暂无分类库存数据</div><div v-if="categorySummary.length" class="category-list"><div v-for="item in categorySummary" :key="item.name" class="category-row"><span>{{ item.name }}</span><b>¥{{ formatMoney(item.value) }}</b><small>{{ item.count }} 个商品</small></div></div></section><section class="subsection"><h3>库存价值前十</h3><div class="table-scroll"><el-table :data="analysis.top10_by_value || []" size="default" stripe height="380" table-layout="fixed"><el-table-column prop="product_name" label="商品" min-width="140" /><el-table-column prop="stock_value" label="库存价值" min-width="120" align="right"><template #default="{ row }">¥{{ formatMoney(row.stock_value) }}</template></el-table-column><el-table-column prop="total_stock" label="数量" min-width="90" align="right" /></el-table></div></section></div>
            <section class="subsection risk-section"><h3>高库存占用风险</h3><el-empty v-if="!riskSummary.length" description="暂无高库存占用风险" :image-size="70" /><div v-else class="risk-list"><div v-for="item in riskSummary" :key="item.product_name" class="risk-row"><div><strong>{{ item.product_name }}</strong><p>库存价值 ¥{{ formatMoney(item.stock_value) }}，当前库存 {{ item.current_stock }}</p></div><el-tag type="warning">占比 {{ item.percentage }}%</el-tag></div></div></section>
          </template>
          <el-empty v-else-if="!analysisLoading" description="暂无库存健康分析数据" />
        </section>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="suggestionVisible" title="滞销商品清仓建议" width="min(680px, calc(100vw - 32px))" draggable><template v-if="clearSuggestion"><el-descriptions :column="2" border><el-descriptions-item label="商品">{{ clearSuggestion.product }}</el-descriptions-item><el-descriptions-item label="当前库存">{{ clearSuggestion.current_stock }}</el-descriptions-item><el-descriptions-item label="库存价值">¥{{ formatMoney(clearSuggestion.stock_value) }}</el-descriptions-item><el-descriptions-item label="当前售价">¥{{ formatMoney(clearSuggestion.current_price) }}</el-descriptions-item></el-descriptions><h3 class="dialog-heading">建议价格</h3><div class="price-grid"><div><span>清仓价</span><b>¥{{ formatMoney(clearSuggestion.suggested_prices?.clearance_price) }}</b></div><div><span>捆绑价</span><b>¥{{ formatMoney(clearSuggestion.suggested_prices?.bundle_price) }}</b></div><div><span>保本价</span><b>¥{{ formatMoney(clearSuggestion.suggested_prices?.break_even_price) }}</b></div></div><h3 class="dialog-heading">行动建议</h3><ul class="suggestions"><li v-for="item in clearSuggestion.suggestions || clearSuggestion.actions || []" :key="item">{{ item }}</li></ul></template></el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { echarts } from '@/utils/charts'
import { ElMessage } from 'element-plus'
import { getClearSuggestion as getClearSuggestionApi, getOverstockAnalysis, getSlowProducts } from '@/api'

const activeTab = ref('slow')
const slowDays = ref(30)
const slowProducts = ref([])
const slowLoading = ref(false)
const slowError = ref('')
const analysis = ref({})
const analysisLoading = ref(false)
const analysisError = ref('')
const categoryChartRef = ref(null)
const suggestionVisible = ref(false)
const clearSuggestion = ref(null)
let categoryChart = null

const formatMoney = value => (Number(value) || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const hasAnalysis = computed(() => Object.keys(analysis.value || {}).length > 0)
const categorySummary = computed(() => Object.entries(analysis.value.by_category || {}).map(([name, data]) => ({ name, value: Number(data?.value) || 0, count: Number(data?.count) || 0 })).sort((a, b) => b.value - a.value))
const riskSummary = computed(() => analysis.value.overstock_products || [])
const healthLevel = computed(() => ({ 优秀: 'health-good', 良好: 'health-ok', 一般: 'health-warn', 较差: 'health-bad' }[analysis.value.health_score?.level] || 'health-neutral'))
const healthTagType = computed(() => ({ 优秀: 'success', 良好: 'success', 一般: 'warning', 较差: 'danger' }[analysis.value.health_score?.level] || 'info'))

function renderCategoryChart() {
  if (!categoryChartRef.value || !categorySummary.value.length) return
  categoryChart?.dispose()
  categoryChart = echarts.init(categoryChartRef.value)
  categoryChart.setOption({ color: ['#165DFF', '#00B42A', '#FF7D00', '#7A5AF8', '#14B8A6'], tooltip: { trigger: 'item', valueFormatter: value => `¥${formatMoney(value)}` }, legend: { bottom: 0, type: 'scroll' }, series: [{ type: 'pie', radius: ['42%', '68%'], label: { formatter: '{b}\n¥{c}' }, data: categorySummary.value }] })
}

async function loadSlowProducts() {
  slowLoading.value = true
  slowError.value = ''
  try { slowProducts.value = await getSlowProducts({ days: slowDays.value }) || [] } catch (error) { slowError.value = error?.message || '滞销商品分析加载失败' } finally { slowLoading.value = false }
}

async function loadOverstock() {
  analysisLoading.value = true
  analysisError.value = ''
  try { analysis.value = await getOverstockAnalysis() || {}; await nextTick(); renderCategoryChart() } catch (error) { analysisError.value = error?.message || '库存健康分析加载失败' } finally { analysisLoading.value = false }
}

async function showClearSuggestion(row) {
  try { clearSuggestion.value = await getClearSuggestionApi(row.product_id); suggestionVisible.value = true } catch { ElMessage.error('清仓建议加载失败') }
}

const onWindowResize = () => categoryChart?.resize()
onMounted(() => { loadSlowProducts(); loadOverstock(); window.addEventListener('resize', onWindowResize) })
onBeforeUnmount(() => { window.removeEventListener('resize', onWindowResize); categoryChart?.dispose() })
</script>

<style scoped>
.analysis-page { display: grid; gap: 16px; }.section-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 16px; }.section-heading h2, .subsection h3 { margin: 3px 0 0; font-size: 20px; }.eyebrow { margin: 0; color: var(--el-text-color-secondary); font-size: 14px; }.actions { display: flex; gap: 10px; }.actions .el-select { width: 150px; }.state-alert { margin-bottom: 16px; }.summary-grid { display: grid; grid-template-columns: repeat(4, minmax(170px, 1fr)); gap: 14px; overflow-x: auto; }.summary-card, .health-card { min-width: 170px; padding: 16px; border: 1px solid var(--el-border-color-lighter); border-radius: 8px; background: var(--el-bg-color); }.summary-card span, .health-card span { color: var(--el-text-color-secondary); font-size: 14px; }.summary-card strong, .health-card strong { display: block; margin-top: 8px; font-size: 25px; }.summary-card.warning { border-color: #FFCC9F; }.health-card { border-color: var(--el-color-info-light-5); }.health-card.health-good { border-color: #A5E8B4; }.health-card.health-warn { border-color: #FFCC9F; }.health-card.health-bad { border-color: #FDB5B5; }.health-card p { margin: 8px 0 0; color: var(--el-text-color-secondary); font-size: 14px; }.analysis-grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(430px, 1fr); gap: 16px; margin-top: 18px; }.subsection { min-width: 0; padding: 16px; border: 1px solid var(--el-border-color-lighter); border-radius: 8px; }.category-chart { height: 260px; }.chart-empty { display: grid; height: 260px; place-items: center; color: var(--el-text-color-secondary); font-size: 14px; }.category-list { display: grid; gap: 6px; }.category-row, .risk-row { display: grid; grid-template-columns: 1fr auto auto; gap: 12px; align-items: center; padding: 10px 0; border-bottom: 1px solid var(--el-border-color-lighter); font-size: 14px; }.category-row:last-child, .risk-row:last-child { border-bottom: 0; }.category-row small { color: var(--el-text-color-secondary); }.table-scroll { overflow-x: auto; }.table-scroll :deep(.el-table) { min-width: 430px; }.risk-section { margin-top: 16px; }.risk-list { margin-top: 10px; }.risk-row { grid-template-columns: 1fr auto; }.risk-row p { margin: 4px 0 0; color: var(--el-text-color-secondary); font-size: 14px; }.risk-text { color: #C45200; font-weight: 700; }.dialog-heading { margin: 20px 0 10px; font-size: 16px; }.price-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }.price-grid > div { padding: 12px; border-radius: 6px; background: var(--el-fill-color-light); }.price-grid span { display: block; color: var(--el-text-color-secondary); font-size: 14px; }.price-grid b { display: block; margin-top: 6px; color: var(--el-color-primary); font-size: 18px; }.suggestions { margin: 0; padding-left: 20px; line-height: 1.8; }
@media (max-width: 920px) { .analysis-grid { grid-template-columns: 1fr; }.summary-grid { grid-template-columns: repeat(4, minmax(180px, 1fr)); } }.analysis-tabs :deep(.el-tabs__item) { min-height: 42px; font-size: 15px; }
</style>
