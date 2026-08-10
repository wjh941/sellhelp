<template>
  <div>
    <el-tabs v-model="activeTab" type="border-card">
      <!-- 滞销商品 -->
      <el-tab-pane label="📦 滞销商品分析" name="slow">
        <div class="page-card">
          <div class="page-header">
            <h2>滞销商品分析</h2>
            <div class="actions">
              <el-select v-model="slowDays" style="width: 140px;">
                <el-option :value="7" label="7天无销量" />
                <el-option :value="30" label="30天无销量" />
                <el-option :value="60" label="60天无销量" />
                <el-option :value="90" label="90天无销量" />
              </el-select>
              <el-button type="primary" @click="loadSlowProducts">分析</el-button>
            </div>
          </div>

          <el-alert v-if="slowProducts.length === 0" type="success" :closable="false" style="margin-bottom: 16px;">
            暂无滞销商品，库存状况良好！
          </el-alert>

          <el-table v-else :data="slowProducts" stripe v-loading="slowLoading">
            <el-table-column prop="product_name" label="商品名称" min-width="150" />
            <el-table-column prop="category" label="分类" width="100">
              <template #default="{ row }">
                <el-tag size="small">{{ row.category }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="current_stock" label="当前库存" width="100">
              <template #default="{ row }">
                <span class="warning-text">{{ row.current_stock }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="stock_value" label="库存价值" width="120">
              <template #default="{ row }">
                <span class="danger-text">¥{{ formatMoney(row.stock_value) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="days_no_sales" label="无销售天数" width="100">
              <template #default="{ row }">
                <el-tag type="warning" size="small">{{ row.days_no_sales }}天</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="total_sales_qty" label="历史销量" width="100" />
            <el-table-column label="操作" width="160">
              <template #default="{ row }">
                <el-button type="primary" size="small" link @click="showClearSuggestion(row)">清仓建议</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <!-- 库存积压分析 -->
      <el-tab-pane label="📊 库存健康分析" name="analysis">
        <div class="page-card">
          <div class="page-header">
            <h2>库存健康分析</h2>
            <el-button type="primary" @click="loadOverstock">重新分析</el-button>
          </div>

          <el-row :gutter="16" class="stat-row">
            <el-col :span="8">
              <div class="health-card" :class="healthLevel">
                <div class="health-score">{{ analysis.health_score?.score || 0 }}</div>
                <div class="health-level">{{ analysis.health_score?.level || '-' }}</div>
                <div class="health-suggestion">{{ analysis.health_score?.suggestion || '暂无数据' }}</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="stat-card blue">
                <div class="stat-value">¥{{ formatMoney(analysis.total_stock_value) }}</div>
                <div class="stat-label">库存总值</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="stat-card orange">
                <div class="stat-value">{{ analysis.product_count }}</div>
                <div class="stat-label">商品数量</div>
              </div>
            </el-col>
          </el-row>

          <el-row :gutter="16">
            <el-col :span="12">
              <div style="margin-top: 16px;">
                <h3>分类库存占比</h3>
                <div ref="categoryChartRef" style="height: 300px;"></div>
              </div>
            </el-col>
            <el-col :span="12">
              <div style="margin-top: 16px;">
                <h3>TOP10高价值商品</h3>
                <el-table :data="analysis.top10_by_value || []" border size="small" max-height="280">
                  <el-table-column prop="product_name" label="商品" min-width="120" />
                  <el-table-column prop="stock_value" label="库存价值" width="120">
                    <template #default="{ row }">¥{{ formatMoney(row.stock_value) }}</template>
                  </el-table-column>
                  <el-table-column prop="total_stock" label="数量" width="80" />
                </el-table>
              </div>
            </el-col>
          </el-row>

          <div v-if="analysis.overstock_products?.length" style="margin-top: 16px;">
            <h3 class="danger-text">⚠️ 库存占比过高商品</h3>
            <el-alert
              v-for="item in analysis.overstock_products"
              :key="item.product_name"
              type="warning"
              :closable="false"
              style="margin-bottom: 8px;"
            >
              <template #title>
                <strong>{{ item.product_name }}</strong> 占比 {{ item.percentage }}%，库存价值 ¥{{ formatMoney(item.stock_value) }}
              </template>
            </el-alert>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 清仓建议对话框 -->
    <el-dialog v-model="suggestionVisible" title="滞销商品清仓建议" width="600px">
      <template v-if="clearSuggestion">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="商品">{{ clearSuggestion.product }}</el-descriptions-item>
          <el-descriptions-item label="当前库存">{{ clearSuggestion.current_stock }}</el-descriptions-item>
          <el-descriptions-item label="库存价值">¥{{ formatMoney(clearSuggestion.stock_value) }}</el-descriptions-item>
          <el-descriptions-item label="当前售价">¥{{ clearSuggestion.current_price }}</el-descriptions-item>
        </el-descriptions>

        <el-divider content-position="left">建议价格</el-divider>
        <el-row :gutter="16">
          <el-col :span="8">
            <div class="price-card">
              <div class="price-label">清仓价</div>
              <div class="price-value">¥{{ clearSuggestion.suggested_prices?.clearance_price }}</div>
              <div class="price-desc">7折快速清仓</div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="price-card">
              <div class="price-label">捆绑价</div>
              <div class="price-value">¥{{ clearSuggestion.suggested_prices?.bundle_price }}</div>
              <div class="price-desc">85折捆绑销售</div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="price-card">
              <div class="price-label">保本价</div>
              <div class="price-value">¥{{ clearSuggestion.suggested_prices?.break_even_price }}</div>
              <div class="price-desc">成本+5%保本</div>
            </div>
          </el-col>
        </el-row>

        <el-divider content-position="left">AI建议</el-divider>
        <ul>
          <li v-for="(s, i) in clearSuggestion.suggestions" :key="i">{{ s }}</li>
        </ul>

        <el-divider content-position="left">行动建议</el-divider>
        <ul>
          <li v-for="(a, i) in clearSuggestion.actions" :key="i" class="action-item">▶ {{ a }}</li>
        </ul>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, computed } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { getSlowProducts, getClearSuggestion as getClearSuggestionApi, getOverstockAnalysis } from '@/api'

const activeTab = ref('slow')
const slowDays = ref(30)
const slowProducts = ref([])
const slowLoading = ref(false)

const analysis = ref({})
const analysisLoading = ref(false)
const categoryChartRef = ref(null)
let categoryChart = null

const suggestionVisible = ref(false)
const clearSuggestion = ref(null)

const formatMoney = (val) => {
  const num = Number(val) || 0
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const healthLevel = computed(() => {
  const level = analysis.value.health_score?.level
  if (level === '优秀') return 'health-good'
  if (level === '良好') return 'health-ok'
  if (level === '一般') return 'health-warn'
  return 'health-bad'
})

const loadSlowProducts = async () => {
  slowLoading.value = true
  try {
    slowProducts.value = await getSlowProducts({ days: slowDays.value })
  } catch (e) { /* handled */ }
  finally {
    slowLoading.value = false
  }
}

const loadOverstock = async () => {
  analysisLoading.value = true
  try {
    analysis.value = await getOverstockAnalysis()
    await nextTick()
    initCategoryChart()
  } catch (e) { /* handled */ }
  finally {
    analysisLoading.value = false
  }
}

const initCategoryChart = () => {
  if (!categoryChartRef.value) return

  categoryChart = echarts.init(categoryChartRef.value)
  const byCategory = analysis.value.by_category || {}
  const pieData = Object.entries(byCategory).map(([name, data]) => ({
    name,
    value: data.value
  }))

  categoryChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: pieData,
      label: { formatter: '{b}\n¥{c}' }
    }]
  })
}

const showClearSuggestion = async (row) => {
  try {
    clearSuggestion.value = await getClearSuggestionApi(row.product_id)
    suggestionVisible.value = true
  } catch (e) { /* handled */ }
}

onMounted(() => {
  loadSlowProducts()
  loadOverstock()

  window.addEventListener('resize', () => {
    categoryChart?.resize()
  })
})
</script>

<style scoped>
.stat-row { margin-bottom: 16px; }
.stat-card {
  border-radius: 8px;
  padding: 16px;
  color: #fff;
  text-align: center;
}
.stat-card .stat-value { font-size: 24px; font-weight: bold; }
.stat-card .stat-label { font-size: 13px; opacity: 0.9; margin-top: 4px; }
.stat-card.blue { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.stat-card.orange { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }

.warning-text { color: #E6A23C; font-weight: bold; }
.danger-text { color: #F56C6C; font-weight: bold; }

.health-card {
  border-radius: 8px;
  padding: 24px;
  text-align: center;
  border: 2px solid;
}
.health-card.health-good { border-color: #67C23A; background: #f0f9eb; }
.health-card.health-ok { border-color: #409EFF; background: #ecf5ff; }
.health-card.health-warn { border-color: #E6A23C; background: #fdf6ec; }
.health-card.health-bad { border-color: #F56C6C; background: #fef0f0; }
.health-score { font-size: 48px; font-weight: bold; }
.health-good .health-score { color: #67C23A; }
.health-ok .health-score { color: #409EFF; }
.health-warn .health-score { color: #E6A23C; }
.health-bad .health-score { color: #F56C6C; }
.health-level { font-size: 18px; font-weight: bold; margin: 8px 0; }
.health-suggestion { font-size: 13px; color: #606266; }

.price-card {
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  padding: 12px;
  text-align: center;
  background: #f5f7fa;
}
.price-label { font-size: 12px; color: #909399; }
.price-value { font-size: 20px; font-weight: bold; color: #409EFF; margin: 8px 0; }
.price-desc { font-size: 11px; color: #909399; }
.action-item { color: #409EFF; line-height: 1.8; }
</style>
