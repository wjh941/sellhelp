<template>
  <section class="sales-page">
    <div class="page-card sales-list-card">
      <header class="page-header">
        <div>
          <p class="section-eyebrow">销售开单</p>
          <h2>销售单据</h2>
        </div>
        <div class="actions">
          <el-button class="primary-action" type="primary" @click="openCreateDialog">
            <el-icon><Plus /></el-icon>新建销售单
          </el-button>
        </div>
      </header>

      <div class="search-bar sales-filters">
        <el-date-picker v-model="filterDate" type="daterange" range-separator="至" start-placeholder="开始日期"
          end-placeholder="结束日期" value-format="YYYY-MM-DD" />
        <el-select v-model="filterCustomer" filterable placeholder="筛选客户" clearable>
          <el-option v-for="customer in customers" :key="customer.id" :label="customer.name" :value="customer.id" />
        </el-select>
        <el-select v-model="filterPayment" placeholder="结算方式" clearable>
          <el-option label="现结" value="现结" />
          <el-option label="赊账" value="赊账" />
          <el-option label="部分结账" value="部分结账" />
        </el-select>
        <el-button type="primary" @click="loadData">查询</el-button>
      </div>

      <div class="table-scroll-wrap">
        <el-table :data="orders" stripe v-loading="loading" row-key="id" class="business-table">
          <el-table-column prop="order_no" label="销售单号" min-width="168" />
          <el-table-column prop="customer_name" label="客户" min-width="160">
            <template #default="{ row }">
              <span>{{ row.customer_name }}</span>
              <el-tag v-if="row.price_level_used" size="small" effect="plain" class="price-level-tag">{{ row.price_level_used }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="销售日期" min-width="154">
            <template #default="{ row }">{{ formatDate(row.sale_date) }}</template>
          </el-table-column>
          <el-table-column prop="total_amount" label="订单金额" width="116" align="right">
            <template #default="{ row }">{{ formatMoney(row.total_amount) }}</template>
          </el-table-column>
          <el-table-column prop="final_amount" label="实收金额" width="116" align="right">
            <template #default="{ row }"><strong class="money-primary">{{ formatMoney(row.final_amount) }}</strong></template>
          </el-table-column>
          <el-table-column prop="payment_type" label="结算方式" width="108">
            <template #default="{ row }">
              <el-tag :type="row.payment_type === '现结' ? 'success' : 'warning'" effect="light">{{ row.payment_type }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="debt_amount" label="欠款" width="112" align="right">
            <template #default="{ row }"><span :class="Number(row.debt_amount) > 0 ? 'money-warning' : ''">{{ formatMoney(row.debt_amount) }}</span></template>
          </el-table-column>
          <el-table-column label="操作" width="178" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link @click="viewDetail(row)">查看</el-button>
              <el-button v-if="row.payment_type !== '现结'" type="success" link @click="handlePay(row)">收款</el-button>
              <el-button type="danger" link @click="handleDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <el-dialog v-model="createDialogVisible" title="新建销售单" width="min(1420px, calc(100vw - 40px))" top="4vh" draggable
      destroy-on-close class="sales-create-dialog" @closed="draggedLineIndex = null">
      <div class="order-workspace">
        <section class="order-column customer-column">
          <div class="column-heading"><span>1</span><div><h3>客户信息</h3><p>选择客户后自动匹配价目</p></div></div>
          <el-form label-position="top" class="compact-form">
            <el-form-item label="客户" required>
              <el-select v-model="newOrder.customer_id" filterable clearable placeholder="输入客户名称搜索" @change="onCustomerChange">
                <el-option v-for="customer in customers" :key="customer.id" :label="customer.name" :value="customer.id">
                  <div class="customer-option"><span>{{ customer.name }}</span><el-tag v-if="customer.is_vip" type="warning" size="small">VIP</el-tag></div>
                </el-option>
              </el-select>
            </el-form-item>
            <el-form-item label="销售日期"><el-date-picker v-model="newOrder.sale_date" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" placeholder="选择日期" /></el-form-item>
            <el-form-item label="操作员"><el-input v-model="newOrder.operator" placeholder="录入操作员" /></el-form-item>
          </el-form>

          <div v-if="currentCustomer" class="customer-summary" :class="{ 'credit-near-limit': isCreditNearLimit }">
            <div><span>客户类型</span><strong>{{ currentCustomer.customer_type || '未分类' }}</strong></div>
            <div><span>执行价格</span><strong>{{ priceLevelLabel }}</strong></div>
            <div><span>当前欠款</span><strong>{{ formatMoney(currentDebt) }}</strong></div>
            <div><span>欠款额度</span><strong>{{ creditLimit ? formatMoney(creditLimit) : '未设置' }}</strong></div>
            <p v-if="isCreditNearLimit" class="credit-warning"><el-icon><WarningFilled /></el-icon>该客户欠款已达到额度的 80%，请确认本单赊销风险。</p>
          </div>
          <el-empty v-else description="请选择客户查看价格与欠款信息" :image-size="78" />
        </section>

        <section class="order-column product-column">
          <div class="column-heading"><span>2</span><div><h3>选择商品</h3><p>选中后立即加入订单</p></div></div>
          <el-select v-model="productSelection" filterable placeholder="输入商品名称或拼音搜索" class="product-select" @change="appendProduct">
            <el-option v-for="product in products" :key="product.id" :label="product.name" :value="product.id">
              <div class="product-option"><span>{{ product.name }}</span><small>库存 {{ product.current_stock ?? '-' }}</small></div>
            </el-option>
          </el-select>
          <p class="selection-hint">商品价格按客户档次自动带入，正式售价请在商品档案中维护。</p>

          <div class="form-divider"></div>
          <el-form label-position="top" class="compact-form">
            <el-form-item label="结算方式" required>
              <el-radio-group v-model="newOrder.payment_type" class="payment-options">
                <el-radio value="现结">现结</el-radio>
                <el-radio value="赊账">赊账</el-radio>
                <el-radio value="部分结账">部分结账</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item v-if="newOrder.payment_type === '部分结账'" label="本次已收金额" required :error="partialPaymentError">
              <el-input-number v-model="newOrder.paid_amount" :min="0" :max="totals.amount" :precision="2" controls-position="right" />
            </el-form-item>
            <el-alert v-if="receivableIncrease > 0" type="warning" :closable="false" show-icon>
              <template #title>本单将使客户应收增加 {{ formatMoney(receivableIncrease) }}</template>
            </el-alert>
            <el-form-item label="订单备注"><el-input v-model="newOrder.remark" type="textarea" :rows="3" placeholder="送货、对账等补充说明" /></el-form-item>
          </el-form>
        </section>

        <section class="order-column preview-column">
          <div class="column-heading"><span>3</span><div><h3>订单预览</h3><p>拖动明细可调整显示顺序</p></div></div>
          <div v-if="newOrder.items.length" class="order-lines" aria-label="订单明细">
            <article v-for="(item, index) in newOrder.items" :key="item.line_id" class="order-line" draggable="true"
              @dragstart="draggedLineIndex = index" @dragover.prevent @drop="dropLine(index)">
              <el-icon class="drag-handle"><Rank /></el-icon>
              <div class="line-main"><strong>{{ item.product_info?.name || '商品' }}</strong><small>库存 {{ item.product_info?.current_stock ?? '-' }} · 成本 {{ formatMoney(item.cost_price) }}</small></div>
              <el-input-number v-model="item.quantity" :min="1" :precision="0" controls-position="right" aria-label="销售数量" />
              <div class="line-amount"><strong>{{ formatMoney(lineAmount(item)) }}</strong><small>{{ formatMoney(item.unit_price) }}/件</small></div>
              <el-button circle text type="danger" aria-label="删除商品" title="删除商品" @click="removeItem(index)"><el-icon><Delete /></el-icon></el-button>
            </article>
          </div>
          <el-empty v-else description="从中间选择商品后会自动加入" :image-size="88" />

          <div class="totals-panel">
            <div><span>订单金额</span><strong>{{ formatMoney(totals.amount) }}</strong></div>
            <div><span>预计毛利</span><strong class="profit-value">{{ formatMoney(totals.profit) }}</strong></div>
          </div>

          <div class="delivery-note">
            <div class="delivery-note-head"><strong>送货单预览</strong><span>{{ currentCustomer?.name || '未选择客户' }}</span></div>
            <div v-for="item in newOrder.items" :key="`note-${item.line_id}`" class="delivery-note-line"><span>{{ item.product_info?.name }}</span><span>{{ item.quantity }} × {{ formatMoney(item.unit_price) }}</span></div>
            <div class="delivery-note-total">合计：{{ formatMoney(totals.amount) }}</div>
            <p v-if="newOrder.remark">备注：{{ newOrder.remark }}</p>
          </div>
          <div class="preview-actions">
            <el-button @click="clearSalesDraft">清空草稿</el-button>
            <el-button type="primary" plain @click="printDeliveryNote"><el-icon><Printer /></el-icon>打印送货单</el-button>
          </div>
        </section>
      </div>

      <template #footer>
        <el-button @click="createDialogVisible = false">暂存并关闭</el-button>
        <el-button class="primary-action" type="primary" :loading="submitting" :disabled="!newOrder.items.length" @click="submitOrder">确认开单</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailVisible" title="销售单详情" width="min(880px, calc(100vw - 32px))">
      <el-descriptions v-if="currentOrder" :column="3" border>
        <el-descriptions-item label="销售单号" :span="2">{{ currentOrder.order_no }}</el-descriptions-item>
        <el-descriptions-item label="客户">{{ currentOrder.customer_name }}</el-descriptions-item>
        <el-descriptions-item label="销售日期" :span="2">{{ formatDate(currentOrder.sale_date) }}</el-descriptions-item>
        <el-descriptions-item label="价格档次">{{ currentOrder.price_level_used }}</el-descriptions-item>
        <el-descriptions-item label="订单金额">{{ formatMoney(currentOrder.total_amount) }}</el-descriptions-item>
        <el-descriptions-item label="实收金额"><strong class="money-primary">{{ formatMoney(currentOrder.final_amount) }}</strong></el-descriptions-item>
        <el-descriptions-item label="结算方式">{{ currentOrder.payment_type }}</el-descriptions-item>
      </el-descriptions>
      <el-divider>商品明细（含 FIFO 批次出库）</el-divider>
      <div class="table-scroll-wrap"><el-table :data="currentOrder?.items || []" border>
        <el-table-column prop="product_name" label="商品" min-width="150" />
        <el-table-column prop="quantity" label="数量" width="86" />
        <el-table-column prop="unit_price" label="售价" width="96"><template #default="{ row }">{{ formatMoney(row.unit_price) }}</template></el-table-column>
        <el-table-column prop="cost_price" label="成本" width="96"><template #default="{ row }">{{ formatMoney(row.cost_price) }}</template></el-table-column>
        <el-table-column prop="profit" label="利润" width="96"><template #default="{ row }"><span class="profit-value">{{ formatMoney(row.profit) }}</span></template></el-table-column>
        <el-table-column label="批次" min-width="180"><template #default="{ row }"><div v-for="batch in (row.batches_used || [])" :key="batch.batch_id"><el-tag size="small">{{ batch.batch_no }}</el-tag> {{ batch.quantity }} @ {{ formatMoney(batch.unit_cost) }}</div><span v-if="!row.batches_used?.length">-</span></template></el-table-column>
      </el-table></div>
    </el-dialog>

    <el-dialog v-model="payDialogVisible" title="收款" width="min(440px, calc(100vw - 32px))">
      <el-form :model="payForm" label-width="92px">
        <el-form-item label="订单金额"><span>{{ formatMoney(payOrder?.final_amount) }}</span></el-form-item>
        <el-form-item label="已收金额"><span>{{ formatMoney(payOrder?.paid_amount) }}</span></el-form-item>
        <el-form-item label="未收金额"><strong class="money-warning">{{ formatMoney((payOrder?.final_amount || 0) - (payOrder?.paid_amount || 0)) }}</strong></el-form-item>
        <el-form-item label="收款方式"><el-radio-group v-model="payForm.payment_type"><el-radio value="现结">现结（全额收款）</el-radio><el-radio value="部分结账">部分结账</el-radio></el-radio-group></el-form-item>
        <el-form-item v-if="payForm.payment_type === '部分结账'" label="收款金额"><el-input-number v-model="payForm.paid_amount" :min="0" :max="remainingPayment" :precision="2" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="payDialogVisible = false">取消</el-button><el-button type="primary" @click="confirmPay">确认收款</el-button></template>
    </el-dialog>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createSalesOrder, deleteSalesOrder, getCustomers, getProducts, getSalesOrder,
  getSalesOrders, updatePayment,
} from '@/api'
import {
  UI_STORAGE_KEYS, buildSalesPayload, getCustomerUnitPrice, getOrderTotals,
  readJson, removeKey, writeJson,
} from '@/utils/operationUi'

const loading = ref(false)
const submitting = ref(false)
const orders = ref([])
const customers = ref([])
const products = ref([])
const filterDate = ref([])
const filterCustomer = ref(null)
const filterPayment = ref('')
const createDialogVisible = ref(false)
const detailVisible = ref(false)
const payDialogVisible = ref(false)
const currentOrder = ref(null)
const payOrder = ref(null)
const productSelection = ref(null)
const draggedLineIndex = ref(null)

const defaultOrder = () => ({
  customer_id: null,
  sale_date: new Date().toISOString().slice(0, 19),
  operator: '',
  remark: '',
  payment_type: '现结',
  paid_amount: 0,
  items: [],
})

const newOrder = reactive(defaultOrder())
const payForm = reactive({ payment_type: '现结', paid_amount: 0 })

const currentCustomer = computed(() => customers.value.find(customer => customer.id === newOrder.customer_id) || null)
const priceLevelLabel = computed(() => {
  if (!currentCustomer.value) return '未选择'
  if (currentCustomer.value.is_vip || currentCustomer.value.customer_type === 'VIP') return 'VIP 价'
  return currentCustomer.value.customer_type === '散户' ? '零售价' : '批发价'
})
const currentDebt = computed(() => Number(currentCustomer.value?.current_debt ?? currentCustomer.value?.debt_amount ?? 0))
const creditLimit = computed(() => Number(currentCustomer.value?.credit_limit ?? currentCustomer.value?.debt_limit ?? 0))
const isCreditNearLimit = computed(() => creditLimit.value > 0 && currentDebt.value / creditLimit.value >= 0.8)
const totals = computed(() => getOrderTotals(newOrder.items))
const receivableIncrease = computed(() => {
  if (newOrder.payment_type === '赊账') return totals.value.amount
  if (newOrder.payment_type === '部分结账') return Math.max(0, totals.value.amount - Number(newOrder.paid_amount || 0))
  return 0
})
const partialPaymentError = computed(() => {
  if (newOrder.payment_type !== '部分结账') return ''
  const paid = Number(newOrder.paid_amount || 0)
  if (paid < 0) return '已收金额不能小于 0'
  if (paid > totals.value.amount) return '已收金额不能超过订单金额'
  return ''
})
const remainingPayment = computed(() => Math.max(0, Number(payOrder.value?.final_amount || 0) - Number(payOrder.value?.paid_amount || 0)))

function createLine(product) {
  return {
    line_id: `${product.id}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    product_id: product.id,
    product_info: product,
    quantity: 1,
    unit_price: Number(getCustomerUnitPrice(product, currentCustomer.value) || 0),
    cost_price: Number(product.purchase_price || 0),
  }
}

const lineAmount = item => Number(item.quantity || 0) * Number(item.unit_price || 0)
const formatMoney = value => `¥${Number(value || 0).toFixed(2)}`
const formatDate = value => value ? new Date(value).toLocaleString('zh-CN') : '-'

const loadData = async () => {
  loading.value = true
  try {
    const params = {}
    if (filterDate.value?.length === 2) {
      params.start_date = filterDate.value[0]
      params.end_date = filterDate.value[1]
    }
    if (filterCustomer.value) params.customer_id = filterCustomer.value
    if (filterPayment.value) params.payment_type = filterPayment.value
    orders.value = await getSalesOrders(params)
  } finally {
    loading.value = false
  }
}

const loadCustomers = async () => { customers.value = await getCustomers() }
const loadProducts = async () => {
  const response = await getProducts({ page_size: 100, is_active: true })
  products.value = response.items || []
}

function resetOrder() {
  Object.assign(newOrder, defaultOrder())
  productSelection.value = null
}

function restoreDraft(draft) {
  const fallback = defaultOrder()
  Object.assign(newOrder, {
    ...fallback,
    ...draft,
    items: (draft.items || []).filter(item => item?.product_id).map(item => ({
      ...item,
      line_id: item.line_id || `${item.product_id}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    })),
  })
}

const openCreateDialog = async () => {
  const draft = readJson(window.localStorage, UI_STORAGE_KEYS.salesDraft, null)
  if (draft?.customer_id || draft?.items?.length) {
    try {
      await ElMessageBox.confirm('检测到一张尚未提交的销售草稿，是否恢复？', '恢复草稿', { confirmButtonText: '恢复草稿', cancelButtonText: '新建空白订单', type: 'info' })
      restoreDraft(draft)
    } catch {
      resetOrder()
    }
  } else {
    resetOrder()
  }
  createDialogVisible.value = true
}

function clearSalesDraft() {
  removeKey(window.localStorage, UI_STORAGE_KEYS.salesDraft)
  resetOrder()
  ElMessage.success('销售草稿已清空')
}

function onCustomerChange() {
  newOrder.items.forEach(item => {
    const product = products.value.find(candidate => candidate.id === item.product_id)
    if (product) item.unit_price = Number(getCustomerUnitPrice(product, currentCustomer.value) || 0)
  })
}

function appendProduct(productId) {
  const product = products.value.find(candidate => candidate.id === productId)
  productSelection.value = null
  if (!product) return
  newOrder.items.push(createLine(product))
}

function removeItem(index) {
  newOrder.items.splice(index, 1)
}

function dropLine(index) {
  const from = draggedLineIndex.value
  if (from == null || from === index) return
  const [moved] = newOrder.items.splice(from, 1)
  newOrder.items.splice(index, 0, moved)
  draggedLineIndex.value = null
}

function clearActiveOrder() {
  resetOrder()
  ElMessage.info('当前销售单已清空')
}

function printDeliveryNote() {
  window.print()
}

const submitOrder = async () => {
  if (!newOrder.customer_id) {
    ElMessage.warning('请选择客户')
    return
  }
  if (!newOrder.items.length || newOrder.items.some(item => !item.product_id || Number(item.quantity) <= 0)) {
    ElMessage.warning('请至少选择一件数量大于 0 的商品')
    return
  }
  if (partialPaymentError.value) {
    ElMessage.warning(partialPaymentError.value)
    return
  }
  try {
    await ElMessageBox.confirm(`确认提交本单 ${formatMoney(totals.value.amount)} 的销售单吗？`, '确认开单', { type: 'warning', confirmButtonText: '确认提交', cancelButtonText: '继续编辑' })
    submitting.value = true
    await createSalesOrder(buildSalesPayload(newOrder))
    removeKey(window.localStorage, UI_STORAGE_KEYS.salesDraft)
    ElMessage.success('开单成功，库存已按 FIFO 自动扣减')
    createDialogVisible.value = false
    await loadData()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      // The API interceptor has already shown the backend error message.
    }
  } finally {
    submitting.value = false
  }
}

const viewDetail = async row => {
  currentOrder.value = await getSalesOrder(row.id)
  detailVisible.value = true
}

function handlePay(row) {
  payOrder.value = row
  Object.assign(payForm, { payment_type: '现结', paid_amount: Number(row.final_amount || 0) - Number(row.paid_amount || 0) })
  payDialogVisible.value = true
}

const confirmPay = async () => {
  try {
    await updatePayment(payOrder.value.id, { payment_type: payForm.payment_type, paid_amount: payForm.paid_amount })
    ElMessage.success('收款成功')
    payDialogVisible.value = false
    await loadData()
  } catch {
    // The API interceptor has already shown the backend error message.
  }
}

const handleDelete = async row => {
  try {
    await ElMessageBox.confirm(`确定删除销售单“${row.order_no}”吗？库存将自动冲回。`, '确认删除', { type: 'warning' })
    await deleteSalesOrder(row.id)
    ElMessage.success('删除成功，库存已冲回')
    await loadData()
  } catch {
    // Cancelled deletion intentionally leaves the list unchanged.
  }
}

const onWindowKeydown = event => {
  if (event.key === 'F5' && !event.ctrlKey && !event.metaKey && !event.altKey && !event.shiftKey) {
    event.preventDefault()
    openCreateDialog()
  }
  if (event.key === 'Escape' && createDialogVisible.value) {
    event.preventDefault()
    clearActiveOrder()
  }
}

// Front-end-only draft: it never enters the API payload and is cleared after a successful sale.
watch(newOrder, value => {
  if (!createDialogVisible.value) return
  writeJson(window.localStorage, UI_STORAGE_KEYS.salesDraft, JSON.parse(JSON.stringify(value)))
}, { deep: true })

onMounted(async () => {
  window.addEventListener('keydown', onWindowKeydown)
  await Promise.all([loadCustomers(), loadProducts()])
  loadData()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onWindowKeydown)
})
</script>

<style scoped>
.sales-page { display: grid; gap: 16px; }
.sales-list-card { padding: 22px; }
.page-header { align-items: center; margin-bottom: 18px; }
.section-eyebrow { margin: 0 0 4px; color: var(--yt-primary); font-size: 14px; font-weight: 700; }
.page-header h2 { margin: 0; color: var(--yt-text); font-size: 22px; }
.primary-action { min-height: 42px; font-size: 15px; }
.sales-filters :deep(.el-select) { width: min(100%, 180px); }
.table-scroll-wrap { overflow-x: auto; }
.business-table { min-width: 920px; }
.price-level-tag { margin-left: 6px; }
.money-primary { color: var(--yt-primary); }
.money-warning { color: var(--yt-warning); font-weight: 700; }
.profit-value { color: var(--yt-success); }
.order-workspace { display: grid; grid-template-columns: minmax(250px, .88fr) minmax(280px, 1fr) minmax(330px, 1.14fr); gap: 16px; }
.order-column { min-width: 0; padding: 16px; border: 1px solid var(--yt-border); border-radius: 8px; background: var(--yt-surface); }
.column-heading { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 18px; }
.column-heading > span { display: grid; place-items: center; width: 28px; height: 28px; border-radius: 50%; color: #fff; background: var(--yt-primary); font-weight: 700; }
.column-heading h3 { margin: 0; color: var(--yt-text); font-size: 17px; }
.column-heading p, .selection-hint { margin: 3px 0 0; color: var(--yt-text-muted); font-size: 14px; line-height: 1.45; }
.compact-form :deep(.el-form-item) { margin-bottom: 15px; }
.compact-form :deep(.el-select), .compact-form :deep(.el-date-editor), .compact-form :deep(.el-input-number) { width: 100%; }
.customer-option, .product-option { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.product-option small { color: var(--yt-text-muted); }
.customer-summary { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; padding: 14px; border: 1px solid var(--yt-border); border-radius: 8px; background: var(--yt-page); }
.customer-summary div { display: grid; gap: 3px; }
.customer-summary span { color: var(--yt-text-muted); font-size: 13px; }
.customer-summary strong { color: var(--yt-text); font-size: 15px; }
.customer-summary.credit-near-limit { border-color: var(--yt-warning); background: color-mix(in srgb, var(--yt-warning) 9%, var(--yt-surface)); }
.credit-warning { grid-column: 1 / -1; display: flex; align-items: flex-start; gap: 5px; margin: 0; color: var(--yt-warning); font-size: 14px; line-height: 1.45; }
.product-select { width: 100%; }
.form-divider { height: 1px; margin: 20px 0; background: var(--yt-border); }
.payment-options { display: flex; flex-wrap: wrap; gap: 4px 12px; }
.order-lines { display: grid; gap: 8px; max-height: 290px; overflow-y: auto; }
.order-line { display: grid; grid-template-columns: auto minmax(0, 1fr) 112px 100px auto; align-items: center; gap: 9px; padding: 10px; border: 1px solid var(--yt-border); border-radius: 6px; cursor: grab; }
.order-line:active { cursor: grabbing; }
.drag-handle { color: var(--yt-text-muted); }
.line-main { min-width: 0; display: grid; gap: 3px; }
.line-main strong { overflow: hidden; color: var(--yt-text); text-overflow: ellipsis; white-space: nowrap; }
.line-main small, .line-amount small { color: var(--yt-text-muted); font-size: 12px; }
.order-line :deep(.el-input-number) { width: 112px; }
.line-amount { display: grid; justify-items: end; gap: 3px; }
.line-amount strong { color: var(--yt-text); }
.totals-panel { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 16px; padding: 14px; border-radius: 6px; background: var(--yt-page); }
.totals-panel div { display: grid; gap: 4px; }
.totals-panel span { color: var(--yt-text-muted); font-size: 13px; }
.totals-panel strong { color: var(--yt-primary); font-size: 20px; }
.delivery-note { margin-top: 14px; padding: 14px; border: 1px dashed var(--yt-border); border-radius: 6px; color: var(--yt-text); font-size: 13px; }
.delivery-note-head, .delivery-note-line, .delivery-note-total { display: flex; justify-content: space-between; gap: 12px; }
.delivery-note-head { padding-bottom: 8px; border-bottom: 1px solid var(--yt-border); }
.delivery-note-head span, .delivery-note p { color: var(--yt-text-muted); }
.delivery-note-line { padding-top: 8px; }
.delivery-note-total { margin-top: 10px; padding-top: 8px; border-top: 1px solid var(--yt-border); font-weight: 700; }
.delivery-note p { margin: 8px 0 0; }
.preview-actions { display: flex; justify-content: flex-end; flex-wrap: wrap; gap: 10px; margin-top: 14px; }
@media (max-width: 1100px) { .order-workspace { grid-template-columns: 1fr; } .order-lines { max-height: none; } }
@media (max-width: 640px) { .sales-list-card { padding: 16px; } .order-line { grid-template-columns: auto minmax(0, 1fr) auto; } .order-line :deep(.el-input-number), .line-amount { grid-column: 2; } .order-line > :last-child { grid-column: 3; grid-row: 1; } }
@media print { .sales-list-card, :deep(.el-overlay:not(.sales-create-dialog)), .preview-actions, :deep(.el-dialog__header), :deep(.el-dialog__footer), .customer-column, .product-column, .totals-panel { display: none !important; } .preview-column { display: block !important; border: 0; } .delivery-note { border-color: #000; } }
</style>
