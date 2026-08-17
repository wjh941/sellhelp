<template>
  <div class="returns-page">
    <section class="page-card">
      <div class="section-heading">
        <div><p class="eyebrow">退货与盘点</p><h2>退货记录</h2></div>
        <div class="actions"><el-button type="primary" @click="openCreateDialog(customerReturnType)"><el-icon><Plus /></el-icon>客户退货</el-button><el-button type="warning" @click="openCreateDialog(supplierReturnType)"><el-icon><RefreshLeft /></el-icon>供应商退货</el-button><el-button @click="openStockTakeDialog"><el-icon><EditPen /></el-icon>库存盘点</el-button></div>
      </div>
      <div class="filter-row"><el-select v-model="filterType" clearable placeholder="全部类型"><el-option :label="customerReturnType" :value="customerReturnType" /><el-option :label="supplierReturnType" :value="supplierReturnType" /></el-select><el-date-picker v-model="filterDate" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" /><el-button type="primary" :loading="loading" @click="loadReturns">查询</el-button></div>
      <el-alert v-if="listError" :title="listError" type="error" show-icon :closable="false" class="state-alert" />
      <div class="table-scroll" v-loading="loading"><el-table v-if="returns.length" :data="returns" stripe height="470" table-layout="fixed"><el-table-column prop="order_no" label="退货单号" min-width="175" fixed="left" /><el-table-column prop="return_type" label="类型" min-width="105"><template #default="{ row }"><el-tag :type="row.return_type === customerReturnType ? 'warning' : 'danger'">{{ row.return_type }}</el-tag></template></el-table-column><el-table-column prop="related_order_no" label="关联单号" min-width="165" /><el-table-column prop="product_name" label="商品" min-width="145" /><el-table-column prop="quantity" label="退货数量" min-width="105" align="right" /><el-table-column prop="refund_amount" label="退款金额" min-width="120" align="right"><template #default="{ row }">¥{{ formatMoney(row.refund_amount) }}</template></el-table-column><el-table-column prop="reason" label="退货原因" min-width="200" show-overflow-tooltip /><el-table-column prop="created_at" label="操作时间" min-width="165"><template #default="{ row }">{{ formatDate(row.created_at) }}</template></el-table-column><el-table-column prop="operator" label="操作员" min-width="110" /></el-table><el-empty v-else-if="!loading && !listError" description="暂无退货记录" /></div>
    </section>

    <el-dialog v-model="createDialogVisible" :title="dialogTitle" width="min(720px, calc(100vw - 32px))" draggable :close-on-click-modal="false">
      <el-form :model="returnForm" label-position="top" class="return-form">
        <div class="form-grid"><el-form-item label="退货类型"><el-tag :type="returnForm.return_type === customerReturnType ? 'warning' : 'danger'">{{ returnForm.return_type }}</el-tag></el-form-item><el-form-item label="关联单号" :required="returnForm.return_type === customerReturnType"><el-input v-model="returnForm.related_order_no" placeholder="原销售单/入库单号" /></el-form-item></div>
        <el-form-item v-if="returnForm.return_type === customerReturnType" label="退货客户" required :error="partnerError"><el-select v-model="returnForm.partner_id" filterable placeholder="选择退货客户"><el-option v-for="customer in customers" :key="customer.id" :label="customer.name" :value="customer.id" /></el-select></el-form-item>
        <el-form-item v-else label="退货供应商" required :error="partnerError"><el-select v-model="returnForm.partner_id" filterable placeholder="选择退货供应商"><el-option v-for="supplier in suppliers" :key="supplier.id" :label="supplier.name" :value="supplier.id" /></el-select></el-form-item>
        <el-form-item label="选择商品" required><el-select v-model="returnForm.product_id" filterable placeholder="输入商品名称搜索" @change="onProductChange"><el-option v-for="product in products" :key="product.id" :label="product.name" :value="product.id"><span>{{ product.name }}</span><small>当前库存 {{ product.current_stock ?? '-' }}</small></el-option></el-select></el-form-item>
        <div v-if="returnForm.product_id" class="stock-context"><span>当前库存：<b>{{ productStockInfo.total_stock ?? 0 }}</b></span><span v-if="returnForm.return_type === supplierReturnType">最大可退：<b>{{ maxReturnQuantity }}</b></span><span v-else>客户退货入库，不受当前库存上限限制</span></div>
        <el-form-item v-if="productStockInfo.batches?.length" label="选择批次"><el-select v-model="returnForm.batch_id" placeholder="不选则按可用批次处理" @change="clearReturnQuantity"><el-option v-for="batch in productStockInfo.batches" :key="batch.batch_id" :label="`${batch.batch_no} - 剩余 ${batch.remaining}`" :value="batch.batch_id" /></el-select></el-form-item>
        <div class="form-grid"><el-form-item label="退货数量" required :error="returnQuantityError"><el-input-number v-model="returnForm.quantity" :min="0" :max="maxReturnQuantity" :precision="2" controls-position="right" /><p v-if="returnQuantityError" class="field-error">{{ returnQuantityError }}</p></el-form-item><el-form-item v-if="returnForm.return_type === supplierReturnType" label="退款金额"><el-input-number v-model="returnForm.refund_amount" :min="0" :precision="2" controls-position="right" /></el-form-item></div>
        <el-form-item label="退货原因"><el-input v-model="returnForm.reason" type="textarea" :rows="3" placeholder="请填写退货原因" /></el-form-item><el-form-item label="操作员"><el-input v-model="returnForm.operator" placeholder="操作员姓名" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="createDialogVisible = false">取消</el-button><el-button type="primary" :disabled="Boolean(returnQuantityError)" @click="submitReturn">确认退货</el-button></template>
    </el-dialog>

    <el-dialog v-model="stockTakeVisible" title="库存盘点" width="min(1050px, calc(100vw - 32px))" top="5vh" draggable :close-on-click-modal="false">
      <el-alert type="info" :closable="false" show-icon title="请录入实际数量。盘点确认后才会提交库存调整。" />
      <div class="table-scroll stocktake-table"><el-table :data="stockTakeItems" border height="500" table-layout="fixed"><el-table-column prop="product_name" label="商品" min-width="150" fixed="left" /><el-table-column prop="batch_no" label="批次" min-width="135" /><el-table-column prop="system_quantity" label="系统数量" min-width="110" align="right" /><el-table-column label="实际数量" min-width="160"><template #default="{ row }"><el-input-number v-model="row.actual_quantity" :min="0" :precision="2" controls-position="right" /><p v-if="stockTakeQuantityError(row)" class="field-error">{{ stockTakeQuantityError(row) }}</p></template></el-table-column><el-table-column label="差异状态" min-width="150"><template #default="{ row }"><el-tag :type="varianceStatus(row).type" effect="light">{{ varianceStatus(row).label }}</el-tag></template></el-table-column><el-table-column label="差异数量" min-width="115" align="right"><template #default="{ row }"><span :class="varianceStatus(row).className">{{ variance(row) ?? '-' }}</span></template></el-table-column><el-table-column label="差异金额" min-width="125" align="right"><template #default="{ row }"><span :class="varianceStatus(row).className">{{ variance(row) === null ? '-' : `¥${formatMoney(variance(row) * (row.unit_price || 0))}` }}</span></template></el-table-column></el-table></div>
      <template #footer><el-button @click="stockTakeVisible = false">取消</el-button><el-button type="primary" :loading="stockTakeSubmitting" @click="confirmStockTakeAction">确认盘点结果</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { confirmStockTake as confirmStockTakeApi, createReturn, getCustomers, getProductStock, getProducts, getReturns, getSuppliers, prepareStockTake } from '@/api'

const customerReturnType = '客户退货'
const supplierReturnType = '供应商退货'
const loading = ref(false)
const listError = ref('')
const returns = ref([])
const products = ref([])
const customers = ref([])
const suppliers = ref([])
const filterType = ref('')
const filterDate = ref([])
const createDialogVisible = ref(false)
const stockTakeVisible = ref(false)
const stockTakeSubmitting = ref(false)
const stockTakeItems = ref([])
const currentReturnType = ref(customerReturnType)
const productStockInfo = ref({ batches: [], total_stock: 0 })
const returnForm = reactive({ return_type: customerReturnType, related_order_no: '', partner_id: null, product_id: null, batch_id: null, quantity: 0, refund_amount: 0, reason: '', operator: '' })

const dialogTitle = computed(() => currentReturnType.value)
const selectedBatch = computed(() => productStockInfo.value.batches?.find(batch => batch.batch_id === returnForm.batch_id))
const maxReturnQuantity = computed(() => {
  if (returnForm.return_type !== supplierReturnType) return undefined
  return Number(selectedBatch.value?.remaining ?? productStockInfo.value.total_stock ?? 0)
})
const returnQuantityError = computed(() => {
  const quantity = Number(returnForm.quantity)
  if (!Number.isFinite(quantity) || quantity <= 0) return '退货数量必须大于 0'
  if (returnForm.return_type === supplierReturnType && quantity > maxReturnQuantity.value) return `退货数量超过当前可退上限 ${maxReturnQuantity.value}`
  return ''
})
const partnerError = computed(() => returnForm.partner_id ? '' : `请选择${returnForm.return_type === customerReturnType ? '退货客户' : '退货供应商'}`)

const formatMoney = value => (Number(value) || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const formatDate = value => value ? new Date(value).toLocaleString('zh-CN') : '-'
function isFiniteNonNegative(value) {
  return value !== null && value !== undefined && !(typeof value === 'string' && value.trim() === '') && Number.isFinite(Number(value)) && Number(value) >= 0
}
const stockTakeQuantityError = row => isFiniteNonNegative(row.actual_quantity) ? '' : '实际数量必须是大于等于 0 的有效数字'
const hasStockTakeErrors = computed(() => stockTakeItems.value.some(item => Boolean(stockTakeQuantityError(item))))
const variance = row => isFiniteNonNegative(row.actual_quantity) ? Number(row.actual_quantity) - Number(row.system_quantity || 0) : null
const varianceStatus = row => {
  const difference = variance(row)
  if (difference === null) return { type: 'danger', label: '数量无效', className: 'variance-loss' }
  if (difference < 0) return { type: 'danger', label: '盘亏', className: 'variance-loss' }
  if (difference > 0) return { type: 'success', label: '盘盈', className: 'variance-profit' }
  return { type: 'info', label: '盘平', className: 'variance-even' }
}

async function loadReturns() {
  loading.value = true
  listError.value = ''
  try {
    const params = {}
    if (filterType.value) params.return_type = filterType.value
    if (filterDate.value?.length === 2) [params.start_date, params.end_date] = filterDate.value
    returns.value = await getReturns(params)
  } catch (error) { listError.value = error?.message || '退货记录加载失败' } finally { loading.value = false }
}

async function loadProducts() {
  try { products.value = (await getProducts({ page_size: 100, is_active: true })).items || [] } catch { ElMessage.error('商品列表加载失败') }
}

async function loadPartners() {
  try {
    const [customerList, supplierList] = await Promise.all([getCustomers(), getSuppliers()])
    customers.value = Array.isArray(customerList) ? customerList : customerList?.items || []
    suppliers.value = Array.isArray(supplierList) ? supplierList : supplierList?.items || []
  } catch { ElMessage.error('客户或供应商列表加载失败') }
}

function openCreateDialog(type) {
  currentReturnType.value = type
  Object.assign(returnForm, { return_type: type, related_order_no: '', partner_id: null, product_id: null, batch_id: null, quantity: 0, refund_amount: 0, reason: '', operator: '' })
  productStockInfo.value = { batches: [], total_stock: 0 }
  createDialogVisible.value = true
}

function clearReturnQuantity() { returnForm.quantity = 0 }
async function onProductChange() {
  clearReturnQuantity()
  if (!returnForm.product_id) return
  try {
    const stock = await getProductStock(returnForm.product_id)
    productStockInfo.value = stock || { batches: [], total_stock: 0 }
    returnForm.batch_id = stock?.batches?.[0]?.batch_id ?? null
  } catch { productStockInfo.value = { batches: [], total_stock: 0 }; ElMessage.error('当前库存读取失败') }
}

async function submitReturn() {
  if (returnForm.return_type === customerReturnType && !returnForm.related_order_no.trim()) { ElMessage.warning('客户退货需要填写原销售单号'); return }
  if (!returnForm.partner_id) { ElMessage.warning(returnForm.return_type === customerReturnType ? '客户退货需要选择客户' : '供应商退货需要选择供应商'); return }
  if (!returnForm.product_id) { ElMessage.warning('请选择商品'); return }
  if (returnQuantityError.value) { ElMessage.warning(returnQuantityError.value); return }
  try {
    await createReturn(returnForm)
    ElMessage.success('退货成功，库存已更新')
    createDialogVisible.value = false
    loadReturns()
  } catch { /* API interceptor displays the failure; keep dialog and entered values intact. */ }
}

async function openStockTakeDialog() {
  try {
    const items = await prepareStockTake()
    stockTakeItems.value = (items || []).map(item => ({ ...item, actual_quantity: item.system_quantity }))
    stockTakeVisible.value = true
  } catch { /* API interceptor displays failure. */ }
}

async function confirmStockTakeAction() {
  if (hasStockTakeErrors.value) { ElMessage.warning('请先修正所有盘点实际数量'); return }
  try {
    await ElMessageBox.confirm('确认盘点结果？系统将根据实际数量调整库存。', '确认盘点', { type: 'warning', confirmButtonText: '确认提交', cancelButtonText: '继续核对' })
    stockTakeSubmitting.value = true
    const items = stockTakeItems.value.map(item => ({ product_id: item.product_id, batch_id: item.batch_id, actual_quantity: Number(item.actual_quantity), reason: '' }))
    await confirmStockTakeApi(items)
    ElMessage.success('盘点完成')
    stockTakeVisible.value = false
  } catch { /* Keep the dialog and quantities when confirmation or submit fails. */ } finally { stockTakeSubmitting.value = false }
}

onMounted(async () => { await Promise.all([loadProducts(), loadPartners()]); loadReturns() })
</script>

<style scoped>
.returns-page { display: grid; gap: 16px; }.section-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 16px; }.section-heading h2 { margin: 3px 0 0; font-size: 20px; }.eyebrow { margin: 0; color: var(--el-text-color-secondary); font-size: 14px; }.actions, .filter-row { display: flex; flex-wrap: wrap; gap: 10px; }.filter-row { margin-bottom: 16px; }.filter-row .el-select { width: 150px; }.state-alert { margin-bottom: 14px; }.table-scroll { overflow-x: auto; }.table-scroll :deep(.el-table) { min-width: 1120px; }.return-form :deep(.el-input__wrapper), .return-form :deep(.el-select__wrapper), .return-form :deep(.el-input-number) { min-height: 42px; width: 100%; }.form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 16px; }.stock-context { display: flex; flex-wrap: wrap; gap: 16px; margin: -6px 0 16px; padding: 12px; border-radius: 6px; background: var(--el-fill-color-light); color: var(--el-text-color-regular); font-size: 14px; }.stock-context b { color: var(--el-color-primary); }.field-error { margin: 6px 0 0; color: #F53F3F; font-size: 14px; }.stocktake-table { margin-top: 16px; }.stocktake-table :deep(.el-table) { min-width: 900px; }.variance-loss { color: #F53F3F; font-weight: 700; }.variance-profit { color: #00B42A; font-weight: 700; }.variance-even { color: var(--el-text-color-secondary); }
@media (max-width: 760px) { .section-heading { align-items: flex-start; flex-direction: column; }.form-grid { grid-template-columns: 1fr; } }
</style>
