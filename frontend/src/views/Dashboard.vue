<template>
  <section class="dashboard-workspace" aria-label="经营看板">
    <div class="dashboard-heading">
      <div>
        <p class="eyebrow">经营看板</p>
        <h1>今日经营与风险提醒</h1>
        <p>聚合库存、销售与应收数据，风险处理仍需在对应业务页面确认。</p>
      </div>
      <div class="heading-actions">
        <el-button :loading="loading" @click="loadData">刷新数据</el-button>
        <el-button v-if="ignoredRiskIds.length" type="warning" plain @click="restoreIgnoredRisks">恢复已忽略风险</el-button>
      </div>
    </div>

    <el-alert
      v-if="loadError"
      class="dashboard-alert"
      type="error"
      :title="loadError"
      description="数据未能完整加载，请检查服务后重试。"
      show-icon
      :closable="false"
    />

    <div class="metric-grid" :class="{ 'is-loading': loading }">
      <button class="metric-card metric-card--primary" type="button" @click="goTo('/sales')">
        <span class="metric-label">今日销售额</span>
        <strong>¥{{ money(todaySales) }}</strong>
        <span class="metric-detail">以今日已完成销售汇总</span>
      </button>
      <button class="metric-card metric-card--success" type="button" @click="goTo('/reports')">
        <span class="metric-label">本周销售额</span>
        <strong>¥{{ money(weekSales) }}</strong>
        <span class="metric-detail">近 7 日销售合计</span>
      </button>
      <button class="metric-card metric-card--warning" type="button" @click="goTo('/finance')">
        <span class="metric-label">总应收欠款</span>
        <strong>¥{{ money(totalDebt) }}</strong>
        <span class="metric-detail">{{ debtCustomers.length }} 位欠款客户</span>
      </button>
      <button class="metric-card metric-card--neutral" type="button" @click="goTo('/stock')">
        <span class="metric-label">库存占用资金</span>
        <strong>¥{{ money(inventoryCapital) }}</strong>
        <span class="metric-detail">当前在库采购成本</span>
      </button>
    </div>

    <div v-if="loading" class="loading-panel">
      <el-skeleton :rows="8" animated />
    </div>

    <template v-else>
      <div class="risk-grid">
        <section class="risk-card">
          <div class="risk-card__header">
            <div>
              <p class="card-kicker card-kicker--danger">效期风险</p>
              <h2>临期商品预警 <el-tag type="danger" effect="light">{{ visibleExpiry.length }} 项</el-tag></h2>
            </div>
            <el-button text @click="toggleSection('expiry')">{{ collapsed.expiry ? '展开' : '收起' }}</el-button>
          </div>
          <div v-show="!collapsed.expiry" class="risk-card__body">
            <el-empty v-if="!visibleExpiry.length" description="暂无需要处理的临期商品" :image-size="64" />
            <div v-else class="risk-list">
              <article v-for="row in visibleExpiry" :key="riskId('expiry', row)" class="risk-row">
                <el-tooltip effect="dark" placement="top-start">
                  <template #content>批次：{{ row.batch_no || row.batch_id || '-' }}<br>到期日：{{ row.expiry_date || '-' }}<br>剩余库存：{{ row.remaining_quantity ?? '-' }}</template>
                  <button class="risk-row__main" type="button" @click="openExpiry(row)">
                    <strong>{{ row.product_name || '未命名商品' }}</strong>
                    <span>{{ expiryDescription(row) }}</span>
                  </button>
                </el-tooltip>
                <el-tag :type="expiryTag(row)" effect="dark">{{ expiryLabel(row) }}</el-tag>
                <div class="risk-row__actions">
                  <el-button text type="primary" @click="openExpiry(row)">查看商品</el-button>
                  <el-button text type="info" @click="dismissRisk('expiry', row)">暂时忽略</el-button>
                </div>
              </article>
            </div>
          </div>
        </section>

        <section class="risk-card">
          <div class="risk-card__header">
            <div>
              <p class="card-kicker card-kicker--warning">补货提醒</p>
              <h2>库存不足 <el-tag type="warning" effect="light">{{ visibleLowStock.length }} 项</el-tag></h2>
            </div>
            <el-button text @click="toggleSection('lowStock')">{{ collapsed.lowStock ? '展开' : '收起' }}</el-button>
          </div>
          <div v-show="!collapsed.lowStock" class="risk-card__body">
            <el-empty v-if="!visibleLowStock.length" description="库存均高于安全库存" :image-size="64" />
            <div v-else class="risk-list">
              <article v-for="row in visibleLowStock" :key="riskId('low-stock', row)" class="risk-row">
                <el-tooltip effect="dark" placement="top-start">
                  <template #content>当前库存：{{ row.current_stock ?? 0 }}<br>安全库存：{{ row.safe_stock ?? 0 }}<br>缺口：{{ stockGap(row) }}</template>
                  <button class="risk-row__main" type="button" @click="openLowStock(row)">
                    <strong>{{ row.product_name || '未命名商品' }}</strong>
                    <span>当前 {{ row.current_stock ?? 0 }}，安全库存 {{ row.safe_stock ?? 0 }}</span>
                  </button>
                </el-tooltip>
                <el-tag type="warning" effect="dark">需补货</el-tag>
                <div class="risk-row__actions">
                  <el-button text type="primary" @click="openLowStock(row)">快速入库</el-button>
                  <el-button text type="info" @click="dismissRisk('low-stock', row)">暂时忽略</el-button>
                </div>
              </article>
            </div>
          </div>
        </section>

        <section class="risk-card">
          <div class="risk-card__header">
            <div>
              <p class="card-kicker card-kicker--warning">应收风险</p>
              <h2>逾期欠款 <el-tag type="warning" effect="light">{{ visibleOverdueDebt.length }} 项</el-tag></h2>
            </div>
            <el-button text @click="toggleSection('debt')">{{ collapsed.debt ? '展开' : '收起' }}</el-button>
          </div>
          <div v-show="!collapsed.debt" class="risk-card__body">
            <el-empty v-if="!visibleOverdueDebt.length" description="暂无逾期欠款" :image-size="64" />
            <div v-else class="risk-list">
              <article v-for="row in visibleOverdueDebt" :key="riskId('debt', row)" class="risk-row">
                <el-tooltip effect="dark" placement="top-start">
                  <template #content>欠款金额：¥{{ money(row.debt ?? row.current_debt) }}<br>逾期天数：{{ row.days_overdue ?? 0 }} 天</template>
                  <button class="risk-row__main" type="button" @click="openDebt(row)">
                    <strong>{{ row.name || row.customer_name || '未命名客户' }}</strong>
                    <span>欠款 ¥{{ money(row.debt ?? row.current_debt) }}，逾期 {{ row.days_overdue ?? 0 }} 天</span>
                  </button>
                </el-tooltip>
                <el-tag type="warning" effect="dark">逾期欠款</el-tag>
                <div class="risk-row__actions">
                  <el-button text type="primary" @click="openDebt(row)">跳转客户</el-button>
                  <el-button text type="info" @click="dismissRisk('debt', row)">暂时忽略</el-button>
                </div>
              </article>
            </div>
          </div>
        </section>

        <section class="risk-card">
          <div class="risk-card__header">
            <div>
              <p class="card-kicker">销售节奏</p>
              <h2>热销与滞销 <el-tag type="info" effect="light">{{ hotProducts.length + slowProducts.length }} 项</el-tag></h2>
            </div>
            <el-button text @click="toggleSection('productTrend')">{{ collapsed.productTrend ? '展开' : '收起' }}</el-button>
          </div>
          <div v-show="!collapsed.productTrend" class="risk-card__body product-trend">
            <div ref="productTrendChartRef" class="chart chart--compact" aria-label="热销和滞销商品图表" />
            <div class="trend-columns">
              <div>
                <h3>本周热销</h3>
                <el-empty v-if="!hotProducts.length" description="暂无销售排行数据" :image-size="48" />
                <button v-for="row in hotProducts.slice(0, 3)" :key="`hot-${row.product_id}`" class="trend-item" type="button" @click="goTo('/sales', { product_id: row.product_id })">
                  <span>{{ row.product_name }}</span><el-tag type="success" size="small">热销</el-tag><strong>¥{{ money(row.amount) }}</strong>
                </button>
              </div>
              <div>
                <h3>30 天滞销</h3>
                <el-empty v-if="!slowProducts.length" description="暂无滞销商品" :image-size="48" />
                <button v-for="row in slowProducts.slice(0, 3)" :key="`slow-${row.product_id}`" class="trend-item" type="button" @click="goTo('/stock', { product_id: row.product_id })">
                  <span>{{ row.product_name }}</span><el-tag type="warning" size="small">30 天滞销</el-tag><strong>¥{{ money(row.stock_value) }}</strong>
                </button>
              </div>
            </div>
          </div>
        </section>
      </div>

      <section class="dashboard-chart-card">
        <div class="risk-card__header">
          <div>
            <p class="card-kicker">销售趋势</p>
            <h2>本周销售走势</h2>
          </div>
          <el-button text type="primary" @click="goTo('/reports')">查看经营周报</el-button>
        </div>
        <div ref="weeklySalesChartRef" class="chart" aria-label="本周销售走势图表" />
      </section>

      <section class="dashboard-chart-card">
        <div class="risk-card__header">
          <div>
            <p class="card-kicker">最近单据</p>
            <h2>最近销售订单</h2>
          </div>
          <el-button text type="primary" @click="goTo('/sales')">查看全部</el-button>
        </div>
        <div class="table-scroll">
          <el-table :data="recentOrders" stripe height="290" empty-text="暂无销售订单" class="data-table">
            <el-table-column prop="order_no" label="单号" min-width="160" />
            <el-table-column prop="customer_name" label="客户" min-width="130" />
            <el-table-column label="金额" min-width="120" align="right">
              <template #default="{ row }">¥{{ money(row.final_amount) }}</template>
            </el-table-column>
            <el-table-column label="结算方式" min-width="108">
              <template #default="{ row }"><el-tag :type="row.payment_type === '现结' ? 'success' : 'warning'">{{ row.payment_type || '未标注' }}</el-tag></template>
            </el-table-column>
            <el-table-column label="开单时间" min-width="170">
              <template #default="{ row }">{{ formatDate(row.sale_date) }}</template>
            </el-table-column>
          </el-table>
        </div>
      </section>
    </template>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import {
  getDashboardMetrics,
  getDebtCustomers,
  getExpiryWarnings,
  getLowStockAlerts,
  getOverdueCustomers,
  getSalesOrders,
  getSlowProducts,
  getStockSummary,
} from '@/api'
import { UI_STORAGE_KEYS, readJson, removeKey, writeJson } from '@/utils/operationUi'

const router = useRouter()
const loading = ref(true)
const loadError = ref('')
const metrics = ref({ daily_sales: [], top_products: [] })
const stockSummary = ref({})
const recentOrders = ref([])
const expiryWarnings = ref([])
const lowStockAlerts = ref([])
const debtCustomers = ref([])
const overdueCustomers = ref([])
const slowProducts = ref([])
const savedIgnoredRiskIds = readJson(window.localStorage, UI_STORAGE_KEYS.ignoredRisks, [])
const ignoredRiskIds = ref(Array.isArray(savedIgnoredRiskIds) ? savedIgnoredRiskIds : [])
const collapsed = ref({ expiry: false, lowStock: false, debt: false, productTrend: false })

const weeklySalesChartRef = ref(null)
const productTrendChartRef = ref(null)
let weeklySalesChart = null
let productTrendChart = null

const asList = value => Array.isArray(value) ? value : Array.isArray(value?.items) ? value.items : []
const number = value => Number(value) || 0
const localDate = (value = new Date()) => {
  const date = value instanceof Date ? value : new Date(value)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}
const money = value => number(value).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const formatDate = value => value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '-'
const todaySales = computed(() => number(asList(metrics.value.daily_sales).find(item => item.date === localDate())?.amount))
const weekSales = computed(() => asList(metrics.value.daily_sales).reduce((total, item) => total + number(item.amount), 0))
const totalDebt = computed(() => debtCustomers.value.reduce((total, item) => total + number(item.current_debt), 0))
const inventoryCapital = computed(() => number(stockSummary.value.total_stock_value))
const hotProducts = computed(() => asList(metrics.value.top_products))
const ignoredSet = computed(() => new Set(ignoredRiskIds.value))

const riskId = (namespace, row) => {
  if (namespace === 'expiry') return `expiry:${row.batch_id || row.batch_no || row.product_id}`
  if (namespace === 'low-stock') return `low-stock:${row.product_id}`
  return `debt:${row.customer_id}`
}
const visibleExpiry = computed(() => expiryWarnings.value.filter(row => !ignoredSet.value.has(riskId('expiry', row))))
const visibleLowStock = computed(() => lowStockAlerts.value.filter(row => !ignoredSet.value.has(riskId('low-stock', row))))
const visibleOverdueDebt = computed(() => overdueCustomers.value.filter(row => !ignoredSet.value.has(riskId('debt', row))))

// Frontend-only risk preferences: never submit these IDs to business APIs.
const dismissRisk = (namespace, row) => {
  const id = riskId(namespace, row)
  if (ignoredSet.value.has(id)) return
  ignoredRiskIds.value = [...ignoredRiskIds.value, id]
  writeJson(window.localStorage, UI_STORAGE_KEYS.ignoredRisks, ignoredRiskIds.value)
}
const restoreIgnoredRisks = () => {
  ignoredRiskIds.value = []
  removeKey(window.localStorage, UI_STORAGE_KEYS.ignoredRisks)
}

const goTo = (path, query = {}) => router.push({ path, query })
const openExpiry = row => goTo('/stock', { product_id: row.product_id })
const openLowStock = row => goTo('/purchase', { product_id: row.product_id })
const openDebt = row => goTo('/finance', { customer_id: row.customer_id })
const toggleSection = async section => {
  collapsed.value[section] = !collapsed.value[section]
  if (section === 'productTrend' && !collapsed.value.productTrend) {
    await nextTick()
    productTrendChart?.resize()
  }
}
const stockGap = row => Math.max(0, number(row.safe_stock) - number(row.current_stock))
const expiryTag = row => row.warning_level === 'expired' || number(row.days_to_expiry) < 0 ? 'danger' : 'warning'
const expiryLabel = row => row.warning_level === 'expired' || number(row.days_to_expiry) < 0 ? '已过期' : `临期 ${row.days_to_expiry ?? 0} 天`
const expiryDescription = row => `${row.expiry_date || '未记录到期日'}到期，剩余 ${row.remaining_quantity ?? 0}`

const disposeChart = chart => chart?.dispose()
const disposeCharts = () => {
  disposeChart(weeklySalesChart)
  disposeChart(productTrendChart)
  weeklySalesChart = null
  productTrendChart = null
}
const chartText = () => getComputedStyle(document.documentElement).getPropertyValue('--color-text').trim() || '#1D2129'
const chartMuted = () => getComputedStyle(document.documentElement).getPropertyValue('--color-muted').trim() || '#86909C'

const renderCharts = () => {
  disposeCharts()
  const textColor = chartText()
  const mutedColor = chartMuted()
  const dailySales = asList(metrics.value.daily_sales)

  if (weeklySalesChartRef.value) {
    weeklySalesChart = echarts.init(weeklySalesChartRef.value)
    weeklySalesChart.setOption({
      tooltip: { trigger: 'axis', valueFormatter: value => `¥${money(value)}` },
      grid: { left: 16, right: 18, top: 24, bottom: 20, containLabel: true },
      xAxis: { type: 'category', data: dailySales.map(item => item.date.slice(5)), axisLabel: { color: mutedColor } },
      yAxis: { type: 'value', axisLabel: { color: mutedColor, formatter: value => `¥${value}` }, splitLine: { lineStyle: { color: 'rgba(134, 144, 156, .16)' } } },
      series: [{ type: 'bar', data: dailySales.map(item => number(item.amount)), barMaxWidth: 34, itemStyle: { color: '#165DFF', borderRadius: [4, 4, 0, 0] } }],
      textStyle: { color: textColor },
    })
  }

  if (productTrendChartRef.value) {
    const hot = hotProducts.value.slice(0, 5)
    const slow = slowProducts.value.slice(0, 5)
    productTrendChart = echarts.init(productTrendChartRef.value)
    productTrendChart.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: value => `¥${money(value)}` },
      legend: { data: ['热销额', '滞销库存值'], textStyle: { color: mutedColor } },
      grid: { left: 12, right: 12, top: 38, bottom: 20, containLabel: true },
      xAxis: { type: 'category', data: [...hot.map(item => item.product_name), ...slow.map(item => item.product_name)], axisLabel: { color: mutedColor, interval: 0, rotate: 20 } },
      yAxis: { type: 'value', axisLabel: { color: mutedColor, formatter: value => `¥${value}` }, splitLine: { lineStyle: { color: 'rgba(134, 144, 156, .16)' } } },
      series: [
        { name: '热销额', type: 'bar', data: [...hot.map(item => number(item.amount)), ...slow.map(() => 0)], itemStyle: { color: '#00B42A' } },
        { name: '滞销库存值', type: 'bar', data: [...hot.map(() => 0), ...slow.map(item => number(item.stock_value))], itemStyle: { color: '#FF7D00' } },
      ],
      textStyle: { color: textColor },
    })
  }
}

const onWindowResize = () => {
  weeklySalesChart?.resize()
  productTrendChart?.resize()
}

const loadData = async () => {
  loading.value = true
  loadError.value = ''
  disposeCharts()
  try {
    const [stock, dashboard, orders, expiry, lowStock, debts, overdue, slow] = await Promise.all([
      getStockSummary(),
      getDashboardMetrics(),
      getSalesOrders({ page_size: 8 }),
      getExpiryWarnings({ warning_days: 30 }),
      getLowStockAlerts(),
      getDebtCustomers(),
      getOverdueCustomers(),
      getSlowProducts(),
    ])
    stockSummary.value = stock || {}
    metrics.value = dashboard || { daily_sales: [], top_products: [] }
    recentOrders.value = asList(orders)
    expiryWarnings.value = asList(expiry)
    lowStockAlerts.value = asList(lowStock)
    debtCustomers.value = asList(debts)
    overdueCustomers.value = asList(overdue)
    slowProducts.value = asList(slow)
    loading.value = false
    await nextTick()
    renderCharts()
  } catch (error) {
    loadError.value = error?.response?.data?.detail || error?.message || '经营看板加载失败'
    disposeCharts()
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
  window.addEventListener('resize', onWindowResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onWindowResize)
  disposeCharts()
})
</script>

<style scoped>
.dashboard-workspace { display: grid; gap: 18px; }
.dashboard-heading, .risk-card__header { align-items: flex-start; display: flex; gap: 16px; justify-content: space-between; }
.dashboard-heading h1 { color: var(--color-text); font-size: 24px; line-height: 1.3; margin: 3px 0 6px; }
.dashboard-heading p:not(.eyebrow) { color: var(--color-muted); font-size: 14px; }
.eyebrow, .card-kicker { color: var(--color-muted); font-size: 13px; font-weight: 600; }
.card-kicker--danger { color: var(--color-danger); }
.card-kicker--warning { color: var(--color-warning); }
.heading-actions { display: flex; flex-wrap: wrap; gap: 10px; justify-content: flex-end; }
.dashboard-alert { margin: 0; }
.metric-grid { display: grid; gap: 14px; grid-template-columns: repeat(4, minmax(0, 1fr)); }
.metric-card { align-items: flex-start; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 8px; color: var(--color-text); cursor: pointer; display: flex; flex-direction: column; min-height: 136px; padding: 18px; text-align: left; transition: box-shadow 160ms ease, transform 160ms ease; }
.metric-card:hover { box-shadow: 0 8px 20px rgba(29, 33, 41, .12); transform: translateY(-2px); }
.metric-card:focus-visible { outline: 2px solid var(--color-warning); outline-offset: 2px; }
.metric-card--primary { border-color: var(--color-primary); }
.metric-card--success { border-color: var(--color-success); }
.metric-card--warning { border-color: var(--color-warning); }
.metric-card--neutral { border-color: #4E5969; }
.metric-label, .metric-detail { color: var(--color-muted); font-size: 14px; }
.metric-card strong { color: var(--color-text); font-size: 25px; line-height: 1.25; margin: 12px 0 8px; }
.metric-detail { margin-top: auto; }
.loading-panel, .risk-card, .dashboard-chart-card { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 8px; padding: 18px; }
.risk-grid { display: grid; gap: 18px; grid-template-columns: repeat(2, minmax(0, 1fr)); }
.risk-card__header h2 { align-items: center; color: var(--color-text); display: flex; flex-wrap: wrap; font-size: 18px; gap: 8px; margin-top: 4px; }
.risk-card__body { border-top: 1px solid var(--color-border); margin-top: 16px; padding-top: 4px; }
.risk-list { display: grid; }
.risk-row { align-items: center; border-bottom: 1px solid var(--color-border); display: grid; gap: 10px; grid-template-columns: minmax(0, 1fr) auto; padding: 12px 0; }
.risk-row:last-child { border-bottom: 0; }
.risk-row__main { background: transparent; border: 0; color: var(--color-text); cursor: pointer; display: grid; gap: 4px; min-width: 0; padding: 0; text-align: left; }
.risk-row__main strong { font-size: 15px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.risk-row__main span { color: var(--color-muted); font-size: 14px; }
.risk-row__actions { display: flex; grid-column: 1 / -1; justify-content: flex-end; }
.product-trend { display: grid; gap: 14px; }
.chart { height: 270px; width: 100%; }
.chart--compact { height: 200px; }
.trend-columns { display: grid; gap: 14px; grid-template-columns: repeat(2, minmax(0, 1fr)); }
.trend-columns h3 { color: var(--color-text); font-size: 15px; margin-bottom: 6px; }
.trend-item { background: transparent; border: 0; border-bottom: 1px solid var(--color-border); color: var(--color-text); cursor: pointer; display: flex; font-size: 14px; justify-content: space-between; padding: 9px 0; text-align: left; width: 100%; }
.trend-item span { overflow: hidden; padding-right: 8px; text-overflow: ellipsis; white-space: nowrap; }
.trend-item strong { color: var(--color-warning); }
.dashboard-chart-card { padding: 18px; }
.table-scroll { overflow-x: auto; }
@media (max-width: 1180px) { .metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 860px) { .dashboard-heading, .risk-card__header { align-items: stretch; flex-direction: column; } .heading-actions { justify-content: flex-start; } .risk-grid { grid-template-columns: 1fr; } }
@media (max-width: 560px) { .metric-grid, .trend-columns { grid-template-columns: 1fr; } .metric-card { min-height: 118px; } }
</style>
