<template>
  <section class="purchase-page">
    <div class="page-card purchase-list-card">
      <header class="page-header">
        <div>
          <p class="section-eyebrow">入库业务</p>
          <h2>入库单据</h2>
        </div>
        <div class="actions">
          <el-button class="primary-action" type="primary" @click="openCreateDialog">
            <el-icon><Plus /></el-icon>新建入库单
          </el-button>
        </div>
      </header>

      <div class="search-bar purchase-filters">
        <el-date-picker v-model="filterDate" type="daterange" range-separator="至"
          start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" />
        <el-select v-model="filterSupplier" filterable placeholder="筛选供应商" clearable>
          <el-option v-for="supplier in suppliers" :key="supplier.id" :label="supplier.name" :value="supplier.id" />
        </el-select>
        <el-button type="primary" @click="loadData">查询</el-button>
      </div>

      <div class="table-scroll-wrap">
        <el-table :data="orders" stripe v-loading="loading" class="business-table" row-key="id">
          <el-table-column prop="order_no" label="入库单号" min-width="176" />
          <el-table-column prop="supplier_name" label="供应商" min-width="160" />
          <el-table-column label="入库日期" min-width="158"><template #default="{ row }">{{ formatDate(row.purchase_date) }}</template></el-table-column>
          <el-table-column prop="total_amount" label="入库金额" width="128" align="right"><template #default="{ row }"><strong class="money-primary">{{ formatMoney(row.total_amount) }}</strong></template></el-table-column>
          <el-table-column prop="operator" label="操作员" width="108" />
          <el-table-column prop="remark" label="备注" min-width="160" show-overflow-tooltip />
          <el-table-column label="操作" width="154" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link @click="viewDetail(row)">查看</el-button>
              <el-button type="danger" link @click="handleDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <el-dialog v-model="createDialogVisible" title="新建入库单" width="min(1220px, calc(100vw - 40px))" top="5vh" draggable
      destroy-on-close class="purchase-create-dialog" @closed="draggedLineIndex = null">
      <div class="purchase-workspace">
        <section class="purchase-column entry-column">
          <div class="column-heading"><span>1</span><div><h3>单据信息</h3><p>选择商品后将直接加入右侧批次明细</p></div></div>
          <el-form label-position="top" class="compact-form">
            <el-form-item label="供应商" required :error="supplierError">
              <el-select v-model="newPurchase.supplier_id" filterable clearable placeholder="输入供应商名称搜索">
                <el-option v-for="supplier in suppliers" :key="supplier.id" :label="supplier.name" :value="supplier.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="采购日期">
              <el-date-picker v-model="newPurchase.purchase_date" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" placeholder="选择采购日期" />
            </el-form-item>
            <el-form-item label="操作员"><el-input v-model="newPurchase.operator" placeholder="录入操作员姓名" /></el-form-item>
            <el-form-item label="单据备注"><el-input v-model="newPurchase.remark" type="textarea" :rows="3" placeholder="送货、对账等补充说明" /></el-form-item>
          </el-form>

          <div class="form-divider"></div>
          <el-form label-position="top" class="compact-form">
            <el-form-item label="添加商品">
              <el-select v-model="productSelection" filterable clearable placeholder="输入商品名称搜索，回车即可添加" @change="appendProduct">
                <el-option v-for="product in products" :key="product.id" :label="product.name" :value="product.id">
                  <div class="product-option"><span>{{ product.name }}</span><small>当前库存 {{ product.current_stock ?? '-' }}</small></div>
                </el-option>
              </el-select>
            </el-form-item>
          </el-form>
          <el-alert type="info" :closable="false" show-icon title="商品选中后会立即生成一条批次明细；可在右侧调整数量、进价及日期。" />
        </section>

        <section class="purchase-column preview-column">
          <div class="column-heading"><span>2</span><div><h3>批次明细预览</h3><p>拖动整行可调整顺序，金额实时计算</p></div></div>
          <div v-if="newPurchase.items.length" class="purchase-lines" aria-label="入库批次明细">
            <article v-for="(item, index) in newPurchase.items" :key="item.line_id" class="purchase-line" draggable="true"
              @dragstart="draggedLineIndex = index" @dragover.prevent @drop="dropLine(index)">
              <el-icon class="drag-handle" aria-label="拖动排序"><Rank /></el-icon>
              <div class="line-product"><strong>{{ item.product_info?.name || '商品' }}</strong><small>批次 {{ item.batch_no || '待填写' }}</small></div>
              <div class="line-field" :class="{ 'has-error': lineErrors(item).batchNo }">
                <span class="line-field-label">批次号</span>
                <el-input v-model="item.batch_no" aria-label="批次号" placeholder="批次号" :class="{ 'is-invalid': lineErrors(item).batchNo }" />
                <p v-if="lineErrors(item).batchNo" class="field-error">{{ lineErrors(item).batchNo }}</p>
              </div>
              <div class="line-field">
                <span class="line-field-label">生产日期</span>
                <el-date-picker v-model="item.production_date" type="date" value-format="YYYY-MM-DD" placeholder="生产日期" aria-label="生产日期" />
              </div>
              <div class="expiry-field" :class="{ 'has-error': lineErrors(item).expiryDate }">
                <span class="line-field-label">到期日期</span>
                <el-date-picker v-model="item.expiry_date" type="date" value-format="YYYY-MM-DD" placeholder="到期日期" aria-label="到期日期" />
                <el-tag :type="expiryStatus(item).type" effect="light">{{ expiryStatus(item).text }}</el-tag>
                <p v-if="lineErrors(item).expiryDate" class="field-error">{{ lineErrors(item).expiryDate }}</p>
              </div>
              <div class="line-field" :class="{ 'has-error': lineErrors(item).quantity }">
                <span class="line-field-label">数量</span>
                <el-input-number v-model="item.quantity" :min="1" :precision="0" controls-position="right" aria-label="入库数量" />
                <p v-if="lineErrors(item).quantity" class="field-error">{{ lineErrors(item).quantity }}</p>
              </div>
              <div class="line-field" :class="{ 'has-error': lineErrors(item).unitPrice }">
                <span class="line-field-label">进价</span>
                <el-input-number v-model="item.unit_price" :min="0.01" :precision="2" controls-position="right" aria-label="入库单价" />
                <p v-if="lineErrors(item).unitPrice" class="field-error">{{ lineErrors(item).unitPrice }}</p>
              </div>
              <strong class="line-amount">{{ formatMoney(lineAmount(item)) }}</strong>
              <el-button type="danger" link title="删除此批次明细" aria-label="删除此批次明细" @click="removeItem(index)">删除</el-button>
            </article>
          </div>
          <el-empty v-else description="从左侧选择商品后，批次明细会自动出现在这里" :image-size="88" />

          <div class="totals-panel">
            <div><span>入库品项</span><strong>{{ newPurchase.items.length }} 项</strong></div>
            <div><span>合计金额</span><strong>{{ formatMoney(totalAmount) }}</strong></div>
          </div>
          <div class="preview-actions"><el-button @click="clearPurchaseDraft">清空草稿</el-button></div>
        </section>
      </div>

      <template #footer>
        <el-button @click="createDialogVisible = false">暂存并关闭</el-button>
        <el-button class="primary-action" type="primary" :loading="submitting" :disabled="!newPurchase.items.length" @click="submitOrder">确认入库</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailVisible" title="入库单详情" width="min(760px, calc(100vw - 32px))">
      <el-descriptions v-if="currentOrder" :column="2" border>
        <el-descriptions-item label="入库单号">{{ currentOrder.order_no }}</el-descriptions-item>
        <el-descriptions-item label="供应商">{{ currentOrder.supplier_name }}</el-descriptions-item>
        <el-descriptions-item label="入库日期">{{ formatDate(currentOrder.purchase_date) }}</el-descriptions-item>
        <el-descriptions-item label="操作员">{{ currentOrder.operator }}</el-descriptions-item>
        <el-descriptions-item label="入库金额" :span="2"><strong class="money-primary">{{ formatMoney(currentOrder.total_amount) }}</strong></el-descriptions-item>
        <el-descriptions-item label="备注" :span="2">{{ currentOrder.remark || '-' }}</el-descriptions-item>
      </el-descriptions>
      <el-divider>商品明细</el-divider>
      <div class="table-scroll-wrap"><el-table :data="currentOrder?.items || []" border class="detail-table">
        <el-table-column prop="product_name" label="商品" min-width="150" />
        <el-table-column prop="batch_no" label="批次号" min-width="120" />
        <el-table-column prop="quantity" label="数量" width="84" />
        <el-table-column prop="unit_price" label="单价" width="96"><template #default="{ row }">{{ formatMoney(row.unit_price) }}</template></el-table-column>
        <el-table-column prop="amount" label="金额" width="104"><template #default="{ row }">{{ formatMoney(row.amount) }}</template></el-table-column>
        <el-table-column label="剩余库存" width="108"><template #default="{ row }"><el-tag :type="row.remaining_quantity > 0 ? 'success' : 'info'">{{ row.remaining_quantity }}</el-tag></template></el-table-column>
      </el-table></div>
    </el-dialog>
  </section>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createPurchaseOrder, deletePurchaseOrder, getProducts, getPurchaseOrder,
  getPurchaseOrders, getSuppliers,
} from '@/api'
import {
  UI_STORAGE_KEYS, buildPurchasePayload, getDaysToExpiry, readJson, removeKey, writeJson,
} from '@/utils/operationUi'

const loading = ref(false)
const submitting = ref(false)
const orders = ref([])
const suppliers = ref([])
const products = ref([])
const filterDate = ref([])
const filterSupplier = ref(null)
const createDialogVisible = ref(false)
const detailVisible = ref(false)
const currentOrder = ref(null)
const productSelection = ref(null)
const draggedLineIndex = ref(null)

const defaultPurchase = () => ({
  supplier_id: null,
  purchase_date: new Date().toISOString().slice(0, 19),
  operator: '',
  remark: '',
  items: [],
})

const newPurchase = reactive(defaultPurchase())
const totalAmount = computed(() => newPurchase.items.reduce((sum, item) => sum + lineAmount(item), 0))
const supplierError = computed(() => newPurchase.supplier_id ? '' : '请选择供应商')

function isFinitePositive(value) {
  return Number.isFinite(Number(value)) && Number(value) > 0
}

function lineErrors(item) {
  const errors = { batchNo: '', quantity: '', unitPrice: '', expiryDate: '' }
  if (!String(item.batch_no || '').trim()) errors.batchNo = '请填写批次号'
  if (!isFinitePositive(item.quantity)) errors.quantity = '数量必须大于 0'
  if (!isFinitePositive(item.unit_price)) errors.unitPrice = '进价必须大于 0'
  if (item.production_date && item.expiry_date && String(item.expiry_date).slice(0, 10) < String(item.production_date).slice(0, 10)) {
    errors.expiryDate = '到期日不能早于生产日'
  }
  return errors
}

const hasPurchaseErrors = computed(() => {
  if (supplierError.value) return true
  return newPurchase.items.some(item => (
    !isFinitePositive(item.quantity) ||
    !isFinitePositive(item.unit_price) ||
    Object.values(lineErrors(item)).some(Boolean)
  ))
})

function createLine(product) {
  return {
    line_id: `${product.id}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    product_id: product.id,
    product_info: product,
    batch_no: '',
    production_date: null,
    expiry_date: null,
    quantity: 1,
    unit_price: Number(product.purchase_price || 1),
    remark: '',
  }
}

const lineAmount = item => Number(item.quantity || 0) * Number(item.unit_price || 0)
const formatMoney = value => `¥${Number(value || 0).toFixed(2)}`
const formatDate = value => value ? new Date(value).toLocaleString('zh-CN') : '-'

function expiryStatus(item) {
  const days = getDaysToExpiry(item.expiry_date)
  if (days == null) return { type: 'info', text: '未填写到期日' }
  if (days < 0) return { type: 'danger', text: `已过期 ${Math.abs(days)} 天` }
  if (days <= 30) return { type: 'warning', text: `临期：剩余 ${days} 天` }
  return { type: 'success', text: `剩余 ${days} 天` }
}

const loadData = async () => {
  loading.value = true
  try {
    const params = {}
    if (filterDate.value?.length === 2) {
      params.start_date = filterDate.value[0]
      params.end_date = filterDate.value[1]
    }
    if (filterSupplier.value) params.supplier_id = filterSupplier.value
    orders.value = await getPurchaseOrders(params)
  } finally {
    loading.value = false
  }
}

const loadSuppliers = async () => { suppliers.value = await getSuppliers() }
const loadProducts = async () => {
  const data = await getProducts({ page_size: 100, is_active: true })
  products.value = data.items || []
}

function resetPurchase() {
  Object.assign(newPurchase, defaultPurchase())
  productSelection.value = null
}

function restoreDraft(draft) {
  const fallback = defaultPurchase()
  Object.assign(newPurchase, {
    ...fallback,
    ...draft,
    items: (draft.items || []).filter(item => item?.product_id).map(item => ({
      ...item,
      line_id: item.line_id || `${item.product_id}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      product_info: products.value.find(product => product.id === item.product_id) || item.product_info,
    })),
  })
}

const openCreateDialog = async () => {
  const draft = readJson(window.localStorage, UI_STORAGE_KEYS.purchaseDraft, null)
  if (draft?.supplier_id || draft?.items?.length) {
    try {
      await ElMessageBox.confirm('检测到一张尚未提交的入库草稿，是否恢复？', '恢复草稿', {
        confirmButtonText: '恢复草稿', cancelButtonText: '新建空白单据', type: 'info',
      })
      restoreDraft(draft)
    } catch {
      resetPurchase()
    }
  } else {
    resetPurchase()
  }
  createDialogVisible.value = true
}

async function clearPurchaseDraft() {
  resetPurchase()
  await nextTick()
  removeKey(window.localStorage, UI_STORAGE_KEYS.purchaseDraft)
  ElMessage.success('入库草稿已清空')
}

function appendProduct(productId) {
  const product = products.value.find(candidate => candidate.id === productId)
  productSelection.value = null
  if (!product) return
  newPurchase.items.push(createLine(product))
}

function removeItem(index) {
  newPurchase.items.splice(index, 1)
}

function dropLine(index) {
  const from = draggedLineIndex.value
  if (from == null || from === index) return
  const [moved] = newPurchase.items.splice(from, 1)
  newPurchase.items.splice(index, 0, moved)
  draggedLineIndex.value = null
}

const submitOrder = async () => {
  if (hasPurchaseErrors.value) {
    ElMessage.warning('请先修正标红的入库信息')
    return
  }
  if (!newPurchase.items.length || newPurchase.items.some(item => !item.product_id)) {
    ElMessage.warning('请至少选择一件商品')
    return
  }
  try {
    await ElMessageBox.confirm(`确认提交本单 ${formatMoney(totalAmount.value)} 的入库单吗？`, '确认入库', {
      type: 'warning', confirmButtonText: '确认提交', cancelButtonText: '继续编辑',
    })
    submitting.value = true
    await createPurchaseOrder(buildPurchasePayload(newPurchase))
    removeKey(window.localStorage, UI_STORAGE_KEYS.purchaseDraft)
    ElMessage.success('入库成功，库存批次已更新')
    createDialogVisible.value = false
    await loadData()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      // API interceptor already provides a user-facing backend error.
    }
  } finally {
    submitting.value = false
  }
}

const viewDetail = async row => {
  currentOrder.value = await getPurchaseOrder(row.id)
  detailVisible.value = true
}

const handleDelete = async row => {
  try {
    await ElMessageBox.confirm(`确定删除入库单“${row.order_no}”吗？`, '确认删除', { type: 'warning' })
    await deletePurchaseOrder(row.id)
    ElMessage.success('删除成功')
    await loadData()
  } catch {
    // Cancelled deletion intentionally leaves the list unchanged.
  }
}

// Front-end-only draft: preview metadata stays in the browser and buildPurchasePayload strips it before submission.
watch(newPurchase, value => {
  if (!createDialogVisible.value) return
  writeJson(window.localStorage, UI_STORAGE_KEYS.purchaseDraft, JSON.parse(JSON.stringify(value)))
}, { deep: true })

onMounted(async () => {
  await Promise.all([loadSuppliers(), loadProducts()])
  loadData()
})
</script>

<style scoped>
.purchase-page { display: grid; gap: 16px; }
.purchase-list-card { padding: 22px; }
.section-eyebrow { margin: 0 0 4px; color: var(--yt-primary); font-size: 14px; font-weight: 700; }
.page-header h2 { margin: 0; color: var(--yt-text); font-size: 22px; }
.primary-action { min-height: 42px; font-size: 15px; }
.purchase-filters :deep(.el-select) { width: min(100%, 190px); }
.table-scroll-wrap { overflow-x: auto; }
.business-table { min-width: 870px; }
.detail-table { min-width: 700px; }
.money-primary { color: var(--yt-primary); }
.purchase-workspace { display: grid; grid-template-columns: minmax(285px, .78fr) minmax(570px, 1.42fr); gap: 16px; }
.purchase-column { min-width: 0; padding: 16px; border: 1px solid var(--yt-border); border-radius: 8px; background: var(--yt-surface); }
.column-heading { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 18px; }
.column-heading > span { display: grid; place-items: center; width: 28px; height: 28px; border-radius: 50%; color: #fff; background: var(--yt-primary); font-weight: 700; }
.column-heading h3 { margin: 0; color: var(--yt-text); font-size: 17px; }
.column-heading p { margin: 3px 0 0; color: var(--yt-text-muted); font-size: 14px; line-height: 1.45; }
.compact-form :deep(.el-form-item) { margin-bottom: 15px; }
.compact-form :deep(.el-form-item__label) { font-size: 15px; }
.compact-form :deep(.el-select), .compact-form :deep(.el-date-editor), .compact-form :deep(.el-input), .compact-form :deep(.el-textarea) { width: 100%; }
.purchase-workspace :deep(.el-select__wrapper),
.purchase-workspace :deep(.el-input__wrapper),
.purchase-workspace :deep(.el-input-number) { min-height: 42px; font-size: 15px; }
.purchase-workspace :deep(.el-input__inner) { font-size: 15px; }
.product-option { display: flex; justify-content: space-between; gap: 12px; }
.product-option small { color: var(--yt-text-muted); }
.form-divider { height: 1px; margin: 20px 0; background: var(--yt-border); }
.purchase-lines { display: grid; gap: 8px; max-height: 510px; overflow-x: auto; overflow-y: auto; padding-right: 3px; }
.purchase-line { display: grid; min-width: 1140px; grid-template-columns: auto minmax(115px, 1fr) minmax(122px, .9fr) 138px minmax(144px, 1.05fr) 112px 112px 90px auto; align-items: start; gap: 9px; padding: 10px; border: 1px solid var(--yt-border); border-radius: 6px; cursor: grab; }
.purchase-line:active { cursor: grabbing; }
.drag-handle { color: var(--yt-text-muted); }
.line-product { display: grid; min-width: 0; gap: 3px; }
.line-product strong { overflow: hidden; color: var(--yt-text); text-overflow: ellipsis; white-space: nowrap; }
.line-product small { color: var(--yt-text-muted); font-size: 12px; }
.purchase-line :deep(.el-date-editor), .purchase-line :deep(.el-input-number), .purchase-line :deep(.el-input) { width: 100%; }
.line-field, .expiry-field { display: grid; gap: 5px; min-width: 0; }
.line-field-label { color: var(--yt-text-muted); font-size: 15px; line-height: 1.25; }
.expiry-field :deep(.el-tag) { justify-self: start; }
.field-error { min-height: 17px; margin: 0; color: var(--color-danger); font-size: 13px; line-height: 1.3; }
.line-field.has-error :deep(.el-input__wrapper), .expiry-field.has-error :deep(.el-input__wrapper), .line-field.has-error :deep(.el-input-number) { box-shadow: 0 0 0 1px var(--color-danger) inset; }
.line-amount { color: var(--yt-primary); text-align: right; }
.totals-panel { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 16px; padding: 14px; border-radius: 6px; background: var(--yt-page); }
.totals-panel div { display: grid; gap: 4px; }
.totals-panel span { color: var(--yt-text-muted); font-size: 13px; }
.totals-panel strong { color: var(--yt-primary); font-size: 20px; }
.preview-actions { display: flex; justify-content: flex-end; margin-top: 14px; }
@media (max-width: 1100px) { .purchase-workspace { grid-template-columns: 1fr; } .purchase-lines { max-height: none; } }
@media (max-width: 760px) { .purchase-list-card { padding: 16px; } .purchase-line { grid-template-columns: auto minmax(0, 1fr) auto; } .purchase-line > :not(.drag-handle):not(.line-product):not(:last-child) { grid-column: 2; } .purchase-line > :last-child { grid-column: 3; grid-row: 1; } .line-amount { text-align: left; } }
</style>
