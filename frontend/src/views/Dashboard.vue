<template>
  <div class="dashboard">
    <el-row :gutter="20" class="stat-row">
      <el-col :span="6">
        <div class="stat-card blue">
          <div class="stat-value">¥{{ formatMoney(stockSummary.total_stock_value) }}</div>
          <div class="stat-label">库存总值</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card green">
          <div class="stat-value">{{ todaySales }}</div>
          <div class="stat-label">今日销售额</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card orange">
          <div class="stat-value">{{ expiryCount }}</div>
          <div class="stat-label">临期预警</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-value">{{ debtCount }}</div>
          <div class="stat-label">欠款客户</div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <el-col :span="16">
        <div class="page-card">
          <div class="page-header">
            <h2>📊 库存分类占比</h2>
          </div>
          <div ref="categoryChartRef" style="height: 300px;"></div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="page-card">
          <div class="page-header">
            <h2>⚠️ 临期预警</h2>
            <el-button type="primary" link @click="$router.push('/stock')">查看详情</el-button>
          </div>
          <el-table :data="expiryWarnings.slice(0, 8)" size="small" stripe>
            <el-table-column prop="product_name" label="商品" min-width="100" />
            <el-table-column label="剩余天数" width="90">
              <template #default="{ row }">
                <el-tag :type="getWarningTag(row.warning_level)" size="small">
                  {{ row.days_to_expiry }}天
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="remaining_quantity" label="数量" width="80" />
          </el-table>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <el-col :span="12">
        <div class="page-card">
          <div class="page-header">
            <h2>💰 本周销售走势</h2>
          </div>
          <div ref="salesChartRef" style="height: 250px;"></div>
        </div>
      </el-col>
      <el-col :span="12">
        <div class="page-card">
          <div class="page-header">
            <h2>🏆 热销商品 TOP5</h2>
          </div>
          <div ref="hotChartRef" style="height: 250px;"></div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <el-col :span="24">
        <div class="page-card">
          <div class="page-header">
            <h2>📝 最近销售订单</h2>
            <el-button type="primary" link @click="$router.push('/sales')">查看全部</el-button>
          </div>
          <el-table :data="recentOrders" stripe style="width: 100%">
            <el-table-column prop="order_no" label="单号" width="180" />
            <el-table-column prop="customer_name" label="客户" min-width="120" />
            <el-table-column prop="final_amount" label="金额" width="120">
              <template #default="{ row }">
                <span style="color: #409EFF;">¥{{ formatMoney(row.final_amount) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="payment_type" label="结算方式" width="100">
              <template #default="{ row }">
                <el-tag :type="row.payment_type === '现结' ? 'success' : 'warning'" size="small">
                  {{ row.payment_type }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="日期" width="160">
              <template #default="{ row }">
                {{ formatDate(row.sale_date) }}
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, shallowRef } from 'vue'
import * as echarts from 'echarts'
import {
  getStockSummary, getExpiryWarnings, getSalesOrders, getReports
} from '@/api'

const stockSummary = ref({})
const expiryWarnings = ref([])
const recentOrders = ref([])
const todaySales = ref('¥0')
const expiryCount = ref(0)
const debtCount = ref(0)

const categoryChartRef = ref(null)
const salesChartRef = ref(null)
const hotChartRef = ref(null)

let categoryChart = null
let salesChart = null
let hotChart = null

const formatMoney = (val) => {
  const num = Number(val) || 0
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const getWarningTag = (level) => {
  if (level === 'expired') return 'danger'
  if (level === 'critical') return 'warning'
  return 'info'
}

const loadData = async () => {
  try {
    // 库存汇总
    const stock = await getStockSummary()
    stockSummary.value = stock

    // 临期预警
    const warnings = await getExpiryWarnings({ warning_days: 30 })
    expiryWarnings.value = warnings
    expiryCount.value = warnings.length

    // 最近销售
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const sales = await getSalesOrders({
      start_date: today.toISOString().split('T')[0],
      page_size: 10
    })
    recentOrders.value = sales.items || sales
    todaySales.value = '¥' + formatMoney(
      (sales.items || sales).reduce((sum, o) => sum + (o.final_amount || 0), 0)
    )

    // 欠款客户统计
    const customers = await (await import('@/api')).getCustomers({ has_debt: true })
    debtCount.value = Array.isArray(customers) ? customers.length : 0

    await nextTick()
    initCharts(stock, warnings)
  } catch (e) {
    console.error('加载数据失败:', e)
  }
}

const initCharts = (stock, warnings) => {
  // 分类饼图
  if (categoryChartRef.value) {
    categoryChart = echarts.init(categoryChartRef.value)
    const categories = stock.by_category || {}
    const pieData = Object.entries(categories).map(([name, value]) => ({
      name,
      value: Math.round(value)
    }))

    categoryChart.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)' },
      legend: { orient: 'vertical', left: 'left' },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        data: pieData,
        emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.5)' } }
      }]
    })
  }

  // 销售走势图（示例数据）
  if (salesChartRef.value) {
    salesChart = echarts.init(salesChartRef.value)
    const days = []
    const amounts = []
    const today = new Date()
    for (let i = 6; i >= 0; i--) {
      const d = new Date(today)
      d.setDate(d.getDate() - i)
      days.push(`${d.getMonth() + 1}/${d.getDate()}`)
      amounts.push(Math.round(Math.random() * 50000 + 20000))
    }

    salesChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: days },
      yAxis: { type: 'value', axisLabel: { formatter: '¥{value}' } },
      series: [{
        data: amounts,
        type: 'line',
        smooth: true,
        areaStyle: { opacity: 0.3 },
        lineStyle: { color: '#409EFF' },
        itemStyle: { color: '#409EFF' }
      }]
    })
  }

  // 热销商品柱状图
  if (hotChartRef.value) {
    hotChart = echarts.init(hotChartRef.value)
    hotChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: ['粮油', '调味', '饮料', '零食', '礼盒'] },
      yAxis: { type: 'value', name: '万元' },
      series: [{
        data: [8.5, 6.2, 4.8, 3.5, 2.1],
        type: 'bar',
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#409EFF' },
            { offset: 1, color: '#67C23A' }
          ])
        }
      }]
    })
  }
}

onMounted(() => {
  loadData()
  window.addEventListener('resize', () => {
    categoryChart?.resize()
    salesChart?.resize()
    hotChart?.resize()
  })
})
</script>

<style scoped>
.stat-row {
  margin-bottom: 20px;
}

.stat-card {
  border-radius: 12px;
  padding: 24px;
  color: #fff;
  text-align: center;

  .stat-value {
    font-size: 32px;
    font-weight: bold;
    margin-bottom: 8px;
  }

  .stat-label {
    font-size: 14px;
    opacity: 0.9;
  }
}
</style>
