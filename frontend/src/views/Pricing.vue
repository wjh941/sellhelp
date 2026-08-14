<template>
  <div>
    <div class="page-card">
      <div class="page-header">
        <h2>AI智能定价（仅供参考，不自动改价）</h2>
      </div>

      <el-alert type="info" :closable="false" style="margin-bottom: 20px;">
        <strong>核心原则：</strong>AI根据历史进价、行情、竞品、周转速度、淡旺季输出三档参考价。
        <strong>最终由老板人工确认修改，系统不会自动改价。</strong>
      </el-alert>

      <div style="display: flex; gap: 10px; margin-bottom: 20px;">
        <el-select v-model="selectedProduct" placeholder="选择商品进行AI定价分析" filterable style="flex: 1;">
          <el-option v-for="p in products" :key="p.id" :label="p.name" :value="p.id">
            <span>{{ p.name }}</span>
            <span style="float: right; color: #909399;">
              零售:¥{{ p.retail_price }} | 批发:¥{{ p.wholesale_price }} | VIP:¥{{ p.vip_price }}
            </span>
          </el-option>
        </el-select>
        <el-button type="primary" @click="analyzePricing" :loading="analyzing">
          <el-icon><MagicStick /></el-icon>
          AI定价分析
        </el-button>
      </div>

      <el-row :gutter="20" v-if="pricingResult">
        <el-col :span="8">
          <div class="pricing-card" style="border-left: 4px solid #F56C6C;">
            <h4>💰 保本底价</h4>
            <div class="pricing-value">¥{{ pricingResult.cost_floor.toFixed(2) }}</div>
            <div class="pricing-desc">不亏钱的底线，低于此价就是赔本</div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="pricing-card" style="border-left: 4px solid #409EFF;">
            <h4>📦 常规批发价</h4>
            <div class="pricing-value">¥{{ pricingResult.normal_price.toFixed(2) }}</div>
            <div class="pricing-desc">普通客户的建议售价</div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="pricing-card" style="border-left: 4px solid #67C23A;">
            <h4>⭐ 大客户价</h4>
            <div class="pricing-value">¥{{ pricingResult.vip_price.toFixed(2) }}</div>
            <div class="pricing-desc">晨升膳食等VIP客户专属价</div>
          </div>
        </el-col>
      </el-row>

      <el-descriptions v-if="pricingResult" :column="2" border style="margin-top: 20px;">
        <el-descriptions-item label="当前零售价">¥{{ pricingResult.current_retail }}</el-descriptions-item>
        <el-descriptions-item label="当前批发价">¥{{ pricingResult.current_wholesale }}</el-descriptions-item>
        <el-descriptions-item label="当前VIP价">¥{{ pricingResult.current_vip }}</el-descriptions-item>
        <el-descriptions-item label="建议调整">
          <el-tag :type="priceChangeType">
            {{ priceChangeText }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>

      <el-card v-if="pricingResult" style="margin-top: 20px;">
        <template #header>
          <strong>🤖 AI分析说明</strong>
        </template>
        <div style="white-space: pre-wrap; line-height: 1.8;">{{ pricingResult.ai_analysis }}</div>
      </el-card>

      <el-card v-if="pricingResult?.factors" style="margin-top: 10px;">
        <template #header>
          <strong>📊 参考因素</strong>
        </template>
        <el-descriptions :column="3" size="small">
          <el-descriptions-item label="成本趋势">
            {{ pricingResult.cost_data?.cost_trend || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="周转状态">
            {{ pricingResult.turnover_data?.turnover_status || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="市场趋势">
            {{ pricingResult.market_data?.market_trend || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="淡旺季">
            {{ pricingResult.season_factor || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="竞品均价">
            ¥{{ pricingResult.market_data?.competitor_avg || 0 }}
          </el-descriptions-item>
          <el-descriptions-item label="周转天数">
            {{ pricingResult.turnover_data?.turnover_days || 0 }}天
          </el-descriptions-item>
        </el-descriptions>
      </el-card>
    </div>

    <div class="page-card" v-if="pricingResult">
      <div class="page-header">
        <h3>📝 人工确认</h3>
        <el-alert type="warning" :closable="false" style="flex: 1; margin-left: 20px;">
          <strong>重要：</strong>AI定价仅为参考，请您手动决定是否调整商品价格。系统不会自动修改。
        </el-alert>
      </div>

      <el-form label-width="150px" inline>
        <el-form-item label="是否采纳AI建议">
          <el-switch v-model="adoptSuggestion" />
        </el-form-item>
        <el-form-item v-if="adoptSuggestion" label="新的零售价">
          <el-input-number v-model="newPrices.retail" :min="0" :precision="2" />
        </el-form-item>
        <el-form-item v-if="adoptSuggestion" label="新的批发价">
          <el-input-number v-model="newPrices.wholesale" :min="0" :precision="2" />
        </el-form-item>
        <el-form-item v-if="adoptSuggestion" label="新的VIP价">
          <el-input-number v-model="newPrices.vip" :min="0" :precision="2" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="confirmAndUpdate" :disabled="!adoptSuggestion">
            应用价格
          </el-button>
        </el-form-item>
      </el-form>

      <el-divider>历史定价参考记录</el-divider>

      <el-table :data="pricingHistory" size="small" stripe>
        <el-table-column prop="product_name" label="商品" min-width="150" />
        <el-table-column prop="cost_floor" label="保本价" width="100">
          <template #default="{ row }">¥{{ row.cost_floor }}</template>
        </el-table-column>
        <el-table-column prop="normal_price" label="批发价" width="100">
          <template #default="{ row }">¥{{ row.normal_price }}</template>
        </el-table-column>
        <el-table-column prop="vip_price" label="VIP价" width="100">
          <template #default="{ row }">¥{{ row.vip_price }}</template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.confirmed ? 'success' : 'info'" size="small">
              {{ row.confirmed ? '已确认' : '待确认' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="分析时间" width="160">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getProducts, calculatePricing, getPricingHistory, updateProduct
} from '@/api'

const products = ref([])
const pricingResult = ref(null)
const pricingHistory = ref([])
const selectedProduct = ref(null)
const analyzing = ref(false)
const adoptSuggestion = ref(false)

const newPrices = reactive({ retail: 0, wholesale: 0, vip: 0 })

const priceChangeType = computed(() => {
  if (!pricingResult.value) return 'info'
  const r = pricingResult.value
  if (r.normal_price > r.current_wholesale * 1.05) return 'warning'
  if (r.normal_price < r.current_wholesale * 0.95) return 'success'
  return 'info'
})

const priceChangeText = computed(() => {
  if (!pricingResult.value) return ''
  const r = pricingResult.value
  if (r.normal_price > r.current_wholesale * 1.05) return '建议提价'
  if (r.normal_price < r.current_wholesale * 0.95) return '建议降价'
  return '价格稳定'
})

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const loadProducts = async () => {
  const data = await getProducts({ page_size: 100, is_active: true })
  products.value = data.items || []
}

const loadHistory = async () => {
  pricingHistory.value = await getPricingHistory({})
}

const analyzePricing = async () => {
  if (!selectedProduct.value) {
    ElMessage.warning('请先选择商品')
    return
  }
  analyzing.value = true
  try {
    pricingResult.value = await calculatePricing(selectedProduct.value)
    newPrices.retail = pricingResult.value.normal_price
    newPrices.wholesale = pricingResult.value.normal_price
    newPrices.vip = pricingResult.value.vip_price
    ElMessage.success('AI定价分析完成')
  } catch (e) { /* handled */ }
  finally {
    analyzing.value = false
  }
}

const confirmAndUpdate = async () => {
  if (!pricingResult.value) return
  try {
    await ElMessageBox.confirm(
      `确认将商品价格更新为：零售¥${newPrices.retail}，批发¥${newPrices.wholesale}，VIP¥${newPrices.vip}？`,
      '确认更新', { type: 'warning' }
    )
    const product = products.value.find(p => p.id === selectedProduct.value)
    if (product) {
      await updateProduct(selectedProduct.value, {
        retail_price: newPrices.retail,
        wholesale_price: newPrices.wholesale,
        vip_price: newPrices.vip
      })
      ElMessage.success('价格已更新')
      loadProducts()
      loadHistory()
    }
  } catch { /* cancelled */ }
}

onMounted(async () => {
  await loadProducts()
  loadHistory()
})
</script>

<style scoped>
.pricing-card {
  background: #fff;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.05);

  h4 {
    color: #606266;
    margin-bottom: 10px;
  }

  .pricing-value {
    font-size: 32px;
    font-weight: bold;
    margin-bottom: 10px;
  }

  .pricing-desc {
    color: #909399;
    font-size: 12px;
  }
}
</style>
