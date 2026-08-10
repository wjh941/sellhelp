<template>
  <div>
    <div class="page-card">
      <div class="page-header">
        <h2>📊 每周经营分析报告</h2>
        <div class="actions">
          <el-button type="primary" @click="generateReport" :loading="generating">
            <el-icon><Refresh /></el-icon>
            {{ report ? '重新生成本周周报' : '生成本周周报' }}
          </el-button>
          <el-select v-model="selectedWeek" style="width: 120px;">
            <el-option v-for="w in weekOptions" :key="w" :label="w" :value="w" />
          </el-select>
        </div>
      </div>

      <div v-if="!report && !generating" style="text-align: center; padding: 60px; color: #909399;">
        <el-icon style="font-size: 60px; margin-bottom: 20px;"><Document /></el-icon>
        <p>还没有周报，点击上方按钮生成本周经营分析报告</p>
      </div>

      <div v-else-if="report" v-loading="loading">
        <el-row :gutter="20" class="stat-row">
          <el-col :span="6">
            <div class="stat-card blue">
              <div class="stat-value">¥{{ formatMoney(report.total_sales) }}</div>
              <div class="stat-label">本周销售额</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-card green">
              <div class="stat-value">¥{{ formatMoney(report.total_profit) }}</div>
              <div class="stat-label">本周利润</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-card">
              <div class="stat-value">{{ report.order_count }}</div>
              <div class="stat-label">订单数</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="stat-card orange">
              <div class="stat-value">¥{{ formatMoney(report.stock_value) }}</div>
              <div class="stat-label">库存总值</div>
            </div>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <div class="page-card" style="margin: 0;">
              <h3>🔥 热销商品 TOP10</h3>
              <el-table :data="hotProducts" size="small" stripe>
                <el-table-column type="index" label="#" width="40" />
                <el-table-column prop="product_name" label="商品" min-width="150" />
                <el-table-column prop="total_amount" label="销售额" width="110">
                  <template #default="{ row }">¥{{ formatMoney(row.total_amount) }}</template>
                </el-table-column>
                <el-table-column prop="total_qty" label="销量" width="80" />
              </el-table>
            </div>
          </el-col>
          <el-col :span="12">
            <div class="page-card" style="margin: 0;">
              <h3>💡 高利润商品 TOP10</h3>
              <el-table :data="profitableProducts" size="small" stripe>
                <el-table-column type="index" label="#" width="40" />
                <el-table-column prop="product_name" label="商品" min-width="150" />
                <el-table-column prop="total_profit" label="利润" width="110">
                  <template #default="{ row }">
                    <span style="color: #67C23A;">¥{{ formatMoney(row.total_profit) }}</span>
                  </template>
                </el-table-column>
                <el-table-column label="利润率" width="90">
                  <template #default="{ row }">
                    <el-tag size="small" :type="row.profit_margin > 20 ? 'success' : row.profit_margin > 10 ? 'warning' : 'danger'">
                      {{ row.profit_margin }}%
                    </el-tag>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <div class="page-card warning-card" v-if="slowProducts.length">
              <h3>⚠️ 滞销商品（30天无销量）</h3>
              <el-table :data="slowProducts" size="small" stripe>
                <el-table-column prop="product_name" label="商品" min-width="150" />
                <el-table-column prop="current_stock" label="库存" width="80" />
                <el-table-column prop="stock_value" label="库存价值" width="110">
                  <template #default="{ row }">
                    <span style="color: #F56C6C;">¥{{ formatMoney(row.stock_value) }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="days_no_sales" label="天数" width="80" />
              </el-table>
            </div>
          </el-col>
          <el-col :span="12">
            <div class="page-card" v-if="overstockItems.length || expiredWarnings.length">
              <h3>🚨 风险预警</h3>
              <el-table :data="riskItems" size="small" stripe>
                <el-table-column prop="type" label="风险类型" width="100">
                  <template #default="{ row }">
                    <el-tag :type="row.type === '临期' ? 'warning' : 'danger'" size="small">
                      {{ row.type }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="name" label="商品" min-width="150" />
                <el-table-column prop="detail" label="详情" min-width="180" />
              </el-table>
              <el-empty v-if="riskItems.length === 0" description="暂无风险" :image-size="80" />
            </div>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <div class="page-card">
              <h3>📋 AI 下周建议</h3>
              <div style="white-space: pre-wrap; line-height: 1.8;">{{ report.suggestions || '暂无建议' }}</div>
            </div>
          </el-col>
          <el-col :span="12">
            <div class="page-card business-advice">
              <h3>🧠 商业思维周报</h3>
              <div style="white-space: pre-wrap; line-height: 1.8;">{{ report.ai_business_advice || '暂无内容' }}</div>
            </div>
          </el-col>
        </el-row>
      </div>
    </div>

    <div class="page-card" v-if="historyReports.length">
      <div class="page-header">
        <h3>📚 历史周报</h3>
      </div>
      <el-table :data="historyReports" size="small">
        <el-table-column prop="week_start" label="周开始" width="110" />
        <el-table-column prop="week_end" label="周结束" width="110" />
        <el-table-column prop="total_sales" label="销售额" width="120">
          <template #default="{ row }">¥{{ formatMoney(row.total_sales) }}</template>
        </el-table-column>
        <el-table-column prop="total_profit" label="利润" width="120">
          <template #default="{ row }">¥{{ formatMoney(row.total_profit) }}</template>
        </el-table-column>
        <el-table-column prop="order_count" label="订单数" width="90" />
        <el-table-column prop="stock_value" label="库存值" width="120">
          <template #default="{ row }">¥{{ formatMoney(row.stock_value) }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="生成时间" width="160">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button type="primary" size="small" link @click="viewReport(row)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { generateReport as generateReportApi, getLatestReport, getReports, getReport } from '@/api'

const report = ref(null)
const historyReports = ref([])
const loading = ref(false)
const generating = ref(false)
const selectedWeek = ref('本周')
const weekOptions = ['本周', '上周', '两周前']

const formatMoney = (val) => {
  const num = Number(val) || 0
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const hotProducts = computed(() => {
  if (!report.value?.hot_products) return []
  try {
    return JSON.parse(report.value.hot_products)
  } catch { return [] }
})

const profitableProducts = computed(() => {
  if (!report.value?.profitable_products) return []
  try {
    return JSON.parse(report.value.profitable_products)
  } catch { return [] }
})

const slowProducts = computed(() => {
  if (!report.value?.slow_products) return []
  try {
    return JSON.parse(report.value.slow_products)
  } catch { return [] }
})

const overstockItems = computed(() => {
  if (!report.value?.overstock_risk) return []
  try {
    return JSON.parse(report.value.overstock_risk)
  } catch { return [] }
})

const expiredWarnings = computed(() => {
  if (!report.value?.expired_warning) return []
  try {
    return JSON.parse(report.value.expired_warning)
  } catch { return [] }
})

const riskItems = computed(() => {
  const items = []
  // 临期
  expiredWarnings.value.forEach(w => {
    items.push({ type: '临期', name: w.product_name, detail: `剩余${w.remaining_quantity}，${w.days_to_expiry}天到期` })
  })
  // 积压
  overstockItems.value.forEach(o => {
    items.push({ type: '积压', name: o.product_name, detail: `库存价值¥${formatMoney(o.stock_value)}` })
  })
  return items
})

const generateReport = async () => {
  generating.value = true
  try {
    // 计算日期范围
    const endDate = new Date()
    let startDate = new Date(endDate)

    if (selectedWeek.value === '上周') {
      endDate.setDate(endDate.getDate() - 7)
      startDate.setDate(endDate.getDate() - 6)
    } else if (selectedWeek.value === '两周前') {
      endDate.setDate(endDate.getDate() - 14)
      startDate.setDate(endDate.getDate() - 13)
    } else {
      startDate.setDate(startDate.getDate() - 6)
    }

    const endStr = endDate.toISOString().split('T')[0]
    report.value = await generateReportApi({ end_date: endStr })
    ElMessage.success('周报生成成功')
    loadHistory()
  } catch (e) { /* handled */ }
  finally {
    generating.value = false
  }
}

const loadLatest = async () => {
  loading.value = true
  try {
    report.value = await getLatestReport()
  } catch (e) {
    // No report yet
  } finally {
    loading.value = false
  }
}

const loadHistory = async () => {
  try {
    historyReports.value = await getReports({ limit: 20 })
  } catch { /* handled */ }
}

const viewReport = async (row) => {
  report.value = await getReport(row.id)
}

onMounted(async () => {
  await loadLatest()
  loadHistory()
})
</script>

<style scoped>
.stat-row { margin-bottom: 20px; }
.warning-card { border-left: 4px solid #F56C6C; }
.business-advice {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  border-radius: 8px;

  h3 { color: #fff; }

  div { color: rgba(255, 255, 255, 0.9); }
}
</style>
