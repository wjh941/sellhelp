<template>
  <div>
    <el-row :gutter="20">
      <el-col :span="6">
        <div class="stat-card blue">
          <div class="stat-value">¥{{ formatMoney(stockSummary.total_stock_value) }}</div>
          <div class="stat-label">库存总值</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card orange">
          <div class="stat-value">{{ expiryWarnings.length }}</div>
          <div class="stat-label">临期预警</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-value">{{ lowStockAlerts.length }}</div>
          <div class="stat-label">低库存商品</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card green">
          <div class="stat-value">{{ Object.keys(stockSummary.by_category || {}).length }}</div>
          <div class="stat-label">商品分类</div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <el-col :span="12">
        <div class="page-card">
          <div class="page-header">
            <h2>📊 分类库存价值</h2>
          </div>
          <div ref="categoryChartRef" style="height: 300px;"></div>
        </div>
      </el-col>
      <el-col :span="12">
        <div class="page-card">
          <div class="page-header">
            <h2>⚠️ 临期预警列表</h2>
          </div>
          <el-table :data="expiryWarnings" size="small" max-height="260">
            <el-table-column prop="product_name" label="商品" min-width="120" />
            <el-table-column label="剩余天数" width="90">
              <template #default="{ row }">
                <el-tag :type="getTagType(row.warning_level)" size="small">{{ row.days_to_expiry }}天</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="remaining_quantity" label="数量" width="80" />
            <el-table-column prop="expiry_date" label="到期日" width="110" />
          </el-table>
        </div>
      </el-col>
    </el-row>

    <div class="page-card">
      <div class="page-header">
        <h2>📦 商品库存明细</h2>
        <div class="actions">
          <el-select v-model="selectedCategory" placeholder="分类筛选" style="width: 150px;" clearable>
            <el-option v-for="(value, key) in categoryStock" :key="key" :label="key" :value="key" />
          </el-select>
          <el-input v-model="searchKeyword" placeholder="搜索商品" style="width: 180px;" clearable />
          <el-button type="primary" @click="loadStockData">刷新</el-button>
          <el-button @click="exportStock">导出Excel</el-button>
        </div>
      </div>

      <el-table :data="filteredStock" stripe v-loading="loading">
        <el-table-column prop="product_name" label="商品名称" min-width="150" />
        <el-table-column label="分类" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ getCategoryByProduct(row.product_id) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="total_stock" label="总库存" width="100">
          <template #default="{ row }">
            <span :class="getStockClass(row.total_stock)">{{ row.total_stock }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="stock_value" label="库存价值" width="120">
          <template #default="{ row }">¥{{ formatMoney(row.stock_value) }}</template>
        </el-table-column>
        <el-table-column label="批次详情" min-width="300">
          <template #default="{ row }">
            <div v-for="b in row.batches.slice(0, 3)" :key="b.batch_id"
              style="display: inline-block; margin-right: 10px; font-size: 12px;">
              <el-tag size="small" :type="getBatchTag(b.days_to_expiry)">
                {{ b.batch_no }} · {{ b.remaining }} · {{ b.days_to_expiry ? b.days_to_expiry + '天到期' : '永不过期' }}
              </el-tag>
            </div>
            <span v-if="row.batches.length > 3" style="color: #909399;">+{{ row.batches.length - 3 }}...</span>
          </template>
        </el-table-column>
        <el-table-column label="风险" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.near_expiry_count > 0" type="warning" size="small">临期{{ row.near_expiry_count }}批</el-tag>
            <el-tag v-else-if="row.expired_count > 0" type="danger" size="small">过期{{ row.expired_count }}批</el-tag>
            <el-tag v-else type="info" size="small">正常</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import {
  getStockSummary, getAllStock, getExpiryWarnings, getLowStockAlerts, getCategoriesStock,
  getCategories
} from '@/api'

const loading = ref(false)
const stockSummary = ref({})
const allStock = ref([])
const expiryWarnings = ref([])
const lowStockAlerts = ref([])
const categoryStock = ref({})
const categories = ref([])
const selectedCategory = ref('')
const searchKeyword = ref('')

const categoryChartRef = ref(null)
let categoryChart = null

const formatMoney = (val) => {
  const num = Number(val) || 0
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const getTagType = (level) => {
  if (level === 'expired') return 'danger'
  if (level === 'critical') return 'warning'
  return 'info'
}

const getBatchTag = (days) => {
  if (days === null || days === undefined) return 'info'
  if (days < 0) return 'danger'
  if (days <= 15) return 'warning'
  if (days <= 30) return ''
  return 'success'
}

const getStockClass = (stock) => {
  if (stock <= 0) return 'tag-danger'
  if (stock < 5) return 'tag-warning'
  return ''
}

const filteredStock = computed(() => {
  let result = allStock.value
  if (searchKeyword.value) {
    result = result.filter(s => s.product_name.includes(searchKeyword.value))
  }
  if (selectedCategory.value) {
    result = result.filter(s => {
      const cat = getCategoryByProduct(s.product_id)
      return cat === selectedCategory.value
    })
  }
  return result
})

const getCategoryByProduct = (productId) => {
  const product = allStock.value.find(s => s.product_id === productId)
  if (!product) return '-'
  const batch = product.batches[0]
  // 需要额外查询分类，这里简化处理
  return categoryStock.value ? Object.keys(categoryStock.value).find(k => true) : '-'
}

const loadStockData = async () => {
  loading.value = true
  try {
    const [summary, stock, warnings, alerts, catStock, cats] = await Promise.all([
      getStockSummary(),
      getAllStock({}),
      getExpiryWarnings({ warning_days: 30 }),
      getLowStockAlerts(),
      getCategoriesStock(),
      getCategories()
    ])
    stockSummary.value = summary
    allStock.value = stock
    expiryWarnings.value = warnings
    lowStockAlerts.value = alerts
    categoryStock.value = catStock
    categories.value = cats

    await nextTick()
    initChart()
  } finally {
    loading.value = false
  }
}

const initChart = () => {
  if (categoryChartRef.value) {
    categoryChart = echarts.init(categoryChartRef.value)
    const data = Object.entries(categoryStock.value).map(([name, info]) => ({
      name,
      value: Math.round(info.total_value)
    }))
    categoryChart.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)' },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        data,
        label: { formatter: '{b}\n¥{c}' }
      }]
    })
  }
}

const exportStock = () => {
  ElMessage.info('导出功能将在后续版本添加')
}

onMounted(() => {
  loadStockData()
  window.addEventListener('resize', () => categoryChart?.resize())
})
</script>

<style scoped>
.stat-row { margin-bottom: 20px; }
</style>
