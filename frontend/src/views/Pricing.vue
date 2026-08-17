<template>
  <div class="pricing-page">
    <section class="page-card">
      <div class="page-header">
        <div>
          <h2>定价参考</h2>
          <p class="page-subtitle">按商品查看采购成本、历史销售与市场行情，辅助人工定价。</p>
        </div>
      </div>
      <el-alert type="warning" :closable="false" show-icon>
        <strong>仅供参考，不会自动修改商品售价。</strong> 模拟预览只保存在当前页面；需要调价请到商品档案手动修改真实售价。
      </el-alert>
      <div class="product-picker">
        <el-select v-model="selectedProduct" placeholder="选择商品进行定价分析" filterable>
          <el-option v-for="product in products" :key="product.id" :label="product.name" :value="product.id">
            <span>{{ product.name }}</span>
            <span class="product-picker__price">零售 {{ formatMoney(product.retail_price) }} | 批发 {{ formatMoney(product.wholesale_price) }} | VIP {{ formatMoney(product.vip_price) }}</span>
          </el-option>
        </el-select>
        <el-button type="primary" size="large" :loading="analyzing" @click="analyzePricing">生成定价参考</el-button>
      </div>
      <el-alert v-if="requestError" type="error" :title="requestError" show-icon :closable="false" class="request-error" />
    </section>

    <template v-if="pricingResult">
      <section class="reference-grid" aria-label="定价参考组成">
        <article class="reference-card cost">
          <div class="reference-card__label">采购进价</div>
          <strong>{{ formatMoney(pricingResult.cost_data?.avg_cost) }}</strong>
          <p>最近进价 {{ formatMoney(pricingResult.cost_data?.latest_cost) }}</p>
          <el-tag size="small" effect="light">{{ pricingResult.cost_data?.cost_trend || '暂无趋势' }}</el-tag>
        </article>
        <article class="reference-card sales">
          <div class="reference-card__label">历史销售区间</div>
          <strong>{{ formatMoney(pricingResult.current_wholesale) }}</strong>
          <p>零售 {{ formatMoney(pricingResult.current_retail) }} · VIP {{ formatMoney(pricingResult.current_vip) }}</p>
          <el-tag size="small" type="success" effect="light">{{ pricingResult.turnover_data?.turnover_status || '暂无周转' }}</el-tag>
        </article>
        <article class="reference-card market">
          <div class="reference-card__label">人工 / 网络行情</div>
          <strong>{{ formatMoney(pricingResult.market_data?.competitor_avg) }}</strong>
          <p>近 30 天 {{ pricingResult.market_data?.recent_records_count || 0 }} 条关联记录</p>
          <el-tag size="small" :type="marketTrendType" effect="light">{{ pricingResult.market_data?.market_trend || '暂无趋势' }}</el-tag>
        </article>
      </section>

      <section class="page-card">
        <div class="section-heading">
          <div><h3>三档参考价</h3><p>参考价来自当前成本、行情与周转，不会自动写回商品档案。</p></div>
          <el-tag type="warning" effect="light">仅供参考，不会自动修改商品售价</el-tag>
        </div>
        <div class="reference-price-grid">
          <article class="price-card floor"><span>保本底价</span><strong>{{ formatMoney(pricingResult.cost_floor) }}</strong><small>不亏损的底线参考</small></article>
          <article class="price-card wholesale"><span>常规批发参考</span><strong>{{ formatMoney(pricingResult.normal_price) }}</strong><small>普通客户参考</small></article>
          <article class="price-card vip"><span>大客户 / VIP 参考</span><strong>{{ formatMoney(pricingResult.vip_price) }}</strong><small>重点客户参考</small></article>
        </div>
      </section>

      <section class="page-card simulation-panel">
        <div class="section-heading">
          <div><h3>价格模拟预览</h3><p>拖动滑块仅模拟批发价和 VIP 价变化，不提交到后端。</p></div>
          <el-tag type="info" effect="light">前端模拟</el-tag>
        </div>
        <div class="simulation-grid">
          <div class="slider-field"><label>批发模拟价 <b>{{ formatMoney(simulationPrices.wholesale) }}</b></label><el-slider v-model="simulationPrices.wholesale" :min="simulationMin" :max="simulationMax" :step="0.1" show-input /></div>
          <div class="slider-field"><label>VIP 模拟价 <b>{{ formatMoney(simulationPrices.vip) }}</b></label><el-slider v-model="simulationPrices.vip" :min="simulationMin" :max="simulationMax" :step="0.1" show-input /></div>
          <div class="margin-summary"><span>批发毛利</span><strong>{{ formatMoney(simulationMargins.wholesale) }}</strong><em>{{ simulationMarginRate.wholesale.toFixed(1) }}%</em></div>
          <div class="margin-summary"><span>VIP 毛利</span><strong>{{ formatMoney(simulationMargins.vip) }}</strong><em>{{ simulationMarginRate.vip.toFixed(1) }}%</em></div>
        </div>
      </section>

      <section class="page-card">
        <div class="section-heading"><div><h3>分析说明</h3><p>以下内容由现有定价接口返回。</p></div></div>
        <el-descriptions :column="3" border class="pricing-factors">
          <el-descriptions-item label="市场趋势">{{ pricingResult.market_data?.market_trend || '-' }}</el-descriptions-item>
          <el-descriptions-item label="周转天数">{{ pricingResult.turnover_data?.turnover_days ?? '-' }} 天</el-descriptions-item>
          <el-descriptions-item label="季节因素">{{ pricingResult.season_factor || '-' }}</el-descriptions-item>
        </el-descriptions>
        <p class="analysis-text">{{ pricingResult.ai_analysis || '暂无分析说明。' }}</p>
      </section>

      <section class="page-card confirmation-panel">
        <div class="section-heading"><div><h3>人工确认参考</h3><p>确认仅标记本次定价参考，不会修改商品真实售价。</p></div></div>
        <el-form inline class="confirm-form">
          <el-form-item label="确认人"><el-input v-model="confirmOperator" placeholder="例如：老板" /></el-form-item>
          <el-form-item><el-button type="primary" size="large" :disabled="!pricingReferenceId" :loading="confirming" @click="confirmReference">确认本次参考</el-button></el-form-item>
        </el-form>
        <p v-if="!pricingReferenceId" class="form-hint">正在匹配本次分析产生的参考记录；未匹配时不会执行确认。</p>
      </section>
    </template>

    <section class="page-card">
      <div class="section-heading"><div><h3>历史定价参考</h3><p>已确认记录只代表人工确认过参考，不代表商品价格已经变化。</p></div></div>
      <el-alert v-if="historyError" type="error" :title="historyError" show-icon :closable="false" class="request-error" />
      <div class="table-scroll">
        <el-table :data="pricingHistory" stripe v-loading="historyLoading" empty-text="暂无定价参考记录">
          <el-table-column prop="product_name" label="商品" min-width="170" />
          <el-table-column prop="cost_floor" label="保本价" width="110"><template #default="{ row }">{{ formatMoney(row.cost_floor) }}</template></el-table-column>
          <el-table-column prop="normal_price" label="批发参考" width="115"><template #default="{ row }">{{ formatMoney(row.normal_price) }}</template></el-table-column>
          <el-table-column prop="vip_price" label="VIP参考" width="110"><template #default="{ row }">{{ formatMoney(row.vip_price) }}</template></el-table-column>
          <el-table-column label="状态" width="110"><template #default="{ row }"><el-tag :type="row.confirmed ? 'success' : 'info'" size="small">{{ row.confirmed ? '已人工确认' : '待确认' }}</el-tag></template></el-table-column>
          <el-table-column label="分析时间" min-width="165"><template #default="{ row }">{{ formatDate(row.created_at || row.reference_date) }}</template></el-table-column>
        </el-table>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { calculatePricing, confirmPricing, getPricingHistory, getProducts } from '@/api'

const products = ref([])
const pricingResult = ref(null)
const pricingHistory = ref([])
const selectedProduct = ref(null)
const analyzing = ref(false)
const historyLoading = ref(false)
const confirming = ref(false)
const pricingReferenceId = ref(null)
const confirmOperator = ref('admin')
const requestError = ref('')
const historyError = ref('')
const simulationPrices = reactive({ wholesale: 0, vip: 0 })

const simulationMin = computed(() => Math.max(0, Number(pricingResult.value?.cost_floor || 0) * 0.8))
const simulationMax = computed(() => Math.max(simulationMin.value + 1, Number(pricingResult.value?.normal_price || 0) * 1.5, Number(pricingResult.value?.vip_price || 0) * 1.5))
const simulationCost = computed(() => Number(pricingResult.value?.cost_floor || pricingResult.value?.cost_data?.avg_cost || 0))
const simulationMargins = computed(() => ({
  wholesale: Number(simulationPrices.wholesale || 0) - simulationCost.value,
  vip: Number(simulationPrices.vip || 0) - simulationCost.value,
}))
const simulationMarginRate = computed(() => ({
  wholesale: Number(simulationPrices.wholesale) > 0 ? simulationMargins.value.wholesale / Number(simulationPrices.wholesale) * 100 : 0,
  vip: Number(simulationPrices.vip) > 0 ? simulationMargins.value.vip / Number(simulationPrices.vip) * 100 : 0,
}))
const marketTrendType = computed(() => pricingResult.value?.market_data?.market_trend === '上涨' ? 'success' : pricingResult.value?.market_data?.market_trend === '下跌' ? 'danger' : 'info')

const formatMoney = value => `¥${(Number(value) || 0).toFixed(2)}`
const formatDate = value => value ? new Date(value).toLocaleString('zh-CN') : '-'
const loadProducts = async () => {
  try { const data = await getProducts({ page_size: 100, is_active: true }); products.value = data.items || [] } catch { requestError.value = '商品列表加载失败，请刷新后重试。' }
}
const loadHistory = async (productId) => {
  historyLoading.value = true
  historyError.value = ''
  try {
    const data = await getPricingHistory(productId ? { product_id: productId } : {})
    pricingHistory.value = productId ? [...data, ...pricingHistory.value.filter(item => item.product_id !== productId)] : data
  } catch { historyError.value = '历史定价参考加载失败，请稍后重试。' } finally { historyLoading.value = false }
}
const analyzePricing = async () => {
  if (!selectedProduct.value) return ElMessage.warning('请先选择商品。')
  analyzing.value = true
  requestError.value = ''
  pricingReferenceId.value = null
  try {
    // Capture existing ids so confirmation can only target the reference created by this analysis.
    const existingReferenceIds = new Set(pricingHistory.value.filter(item => item.product_id === selectedProduct.value).map(item => item.id))
    pricingResult.value = await calculatePricing(selectedProduct.value)
    simulationPrices.wholesale = Number(pricingResult.value.normal_price || 0)
    simulationPrices.vip = Number(pricingResult.value.vip_price || 0)
    const latestProductHistory = await getPricingHistory({ product_id: selectedProduct.value })
    pricingReferenceId.value = latestProductHistory.find(item => !existingReferenceIds.has(item.id))?.id || null
    pricingHistory.value = [...latestProductHistory, ...pricingHistory.value.filter(item => item.product_id !== selectedProduct.value)]
    ElMessage.success('定价参考已生成。')
  } catch { requestError.value = '定价参考生成失败，请稍后重试。' } finally { analyzing.value = false }
}
const confirmReference = async () => {
  if (!pricingReferenceId.value) return ElMessage.warning('未找到可确认的定价参考记录。')
  try {
    await ElMessageBox.confirm('确认后仅标记本次定价参考，不会修改商品售价。', '确认定价参考', { type: 'warning' })
    confirming.value = true
    await confirmPricing(pricingReferenceId.value, confirmOperator.value || 'admin')
    ElMessage.success('定价参考已人工确认，商品售价未修改。')
    await loadHistory(selectedProduct.value)
  } catch { /* Cancelled or Axios interceptor already reported the error. */ } finally { confirming.value = false }
}

onMounted(async () => { await Promise.all([loadProducts(), loadHistory()]) })
</script>

<style scoped>
.pricing-page { display: grid; gap: 20px; }
.page-subtitle, .section-heading p, .form-hint { color: var(--color-muted); font-size: 14px; margin-top: 6px; }
.product-picker { display: flex; gap: 12px; margin-top: 18px; }
.product-picker :deep(.el-select) { flex: 1; }
.product-picker :deep(.el-input__wrapper), .product-picker :deep(.el-select__wrapper) { min-height: 44px; }
.product-picker__price { color: var(--color-muted); float: right; font-size: 14px; }
.request-error { margin-top: 16px; }
.reference-grid, .reference-price-grid { display: grid; gap: 16px; grid-template-columns: repeat(3, minmax(0, 1fr)); }
.reference-card, .price-card { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 8px; min-height: 148px; padding: 18px; }
.reference-card { box-shadow: 0 4px 12px rgba(29, 33, 41, .05); }
.reference-card.cost { background: color-mix(in srgb, var(--color-warning) 6%, var(--color-surface)); }.reference-card.sales { background: color-mix(in srgb, var(--color-success) 6%, var(--color-surface)); }.reference-card.market { background: color-mix(in srgb, var(--color-primary) 6%, var(--color-surface)); }
.reference-card__label, .price-card span { color: var(--color-muted); font-size: 14px; }
.reference-card strong, .price-card strong { display: block; font-size: 28px; margin: 12px 0 8px; }
.reference-card p, .price-card small { color: var(--el-text-color-regular); display: block; font-size: 14px; min-height: 22px; }
.section-heading { align-items: flex-start; display: flex; gap: 16px; justify-content: space-between; margin-bottom: 18px; }.section-heading h3 { font-size: 17px; }
.price-card.floor { background: color-mix(in srgb, var(--color-warning) 7%, var(--color-surface)); }.price-card.wholesale { background: color-mix(in srgb, var(--color-primary) 7%, var(--color-surface)); }.price-card.vip { background: color-mix(in srgb, var(--color-success) 7%, var(--color-surface)); }
.simulation-grid { display: grid; gap: 22px; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }.slider-field label { display: flex; font-size: 15px; justify-content: space-between; margin-bottom: 12px; }.slider-field :deep(.el-input-number) { width: 112px; }.margin-summary { align-items: baseline; background: var(--el-fill-color-light); border-radius: 6px; display: flex; gap: 10px; padding: 14px; }.margin-summary span { color: var(--color-muted); }.margin-summary strong { font-size: 20px; }.margin-summary em { color: var(--color-success); font-size: 15px; font-style: normal; }
.pricing-factors { font-size: 14px; }.analysis-text { line-height: 1.8; margin-top: 18px; white-space: pre-wrap; }.confirm-form :deep(.el-input__wrapper) { min-height: 42px; }.table-scroll { overflow-x: auto; }.table-scroll :deep(.el-table) { min-width: 760px; }
@media (max-width: 900px) { .reference-grid, .reference-price-grid { grid-template-columns: 1fr; }.simulation-grid { grid-template-columns: 1fr; } }.product-picker { flex-direction: column; }
</style>
