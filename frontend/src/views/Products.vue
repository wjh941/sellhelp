<template>
  <div class="archive-page">
    <section class="page-card archive-workspace">
      <div class="page-header">
        <div>
          <p class="section-kicker">基础档案</p>
          <h2>商品档案</h2>
          <p class="section-description">统一维护价格、库存安全线与临期提醒。</p>
        </div>
        <div class="archive-actions">
          <el-radio-group v-model="viewMode" class="view-mode" aria-label="商品显示方式" @change="savePreferences">
            <el-radio-button value="table">表格</el-radio-button>
            <el-radio-button value="card">卡片</el-radio-button>
          </el-radio-group>
          <el-popover placement="bottom-end" :width="250" trigger="click">
            <template #reference>
              <el-button plain aria-label="商品列表显示设置"><el-icon><Setting /></el-icon>列表设置</el-button>
            </template>
            <div class="column-panel">
              <strong>显示列</strong>
              <el-checkbox-group v-model="visibleColumns" @change="savePreferences">
                <el-checkbox v-for="column in optionalColumns" :key="column.key" :value="column.key">{{ column.label }}</el-checkbox>
              </el-checkbox-group>
              <el-button text type="primary" @click="resetPreferences">恢复默认显示</el-button>
            </div>
          </el-popover>
          <el-button type="primary" @click="openDialog()"><el-icon><Plus /></el-icon>新增商品</el-button>
        </div>
      </div>

      <div class="filter-bar">
        <el-input v-model="searchKeyword" placeholder="商品名称或编码" clearable @keyup.enter="reloadData">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="filterCategory" placeholder="全部分类" clearable @change="reloadData">
          <el-option v-for="cat in categories" :key="cat.id" :label="cat.name" :value="cat.id" />
        </el-select>
        <el-switch v-model="filterActive" active-text="在售商品" inactive-text="全部状态" @change="reloadData" />
        <el-button type="primary" @click="reloadData">查询</el-button>
      </div>
      <p v-if="preferenceMessage" class="preference-message" role="status">{{ preferenceMessage }}</p>
      <el-alert v-if="loadError" :title="loadError" type="error" :closable="false" show-icon class="archive-alert" />

      <div v-if="viewMode === 'table'" class="archive-table-scroll">
        <el-table :data="orderedProducts" stripe highlight-current-row class="data-table" min-width="1280" v-loading="loading" empty-text="暂无符合条件的商品">
          <el-table-column v-if="isColumnVisible('code')" prop="code" label="编码" width="145" />
          <el-table-column prop="name" label="商品名称" min-width="190">
            <template #default="{ row }">
              <div class="product-name"><strong>{{ row.name }}</strong><small>{{ row.spec || '未填写规格' }} · {{ row.unit || '-' }}</small></div>
            </template>
          </el-table-column>
          <el-table-column v-if="isColumnVisible('category')" prop="category_name" label="分类" width="105">
            <template #default="{ row }"><el-tag size="small" effect="plain">{{ row.category_name || '未分类' }}</el-tag></template>
          </el-table-column>
          <el-table-column label="库存 / 安全线" min-width="180">
            <template #default="{ row }">
              <el-tooltip :content="`当前库存 ${quantity(row.current_stock)}，安全库存 ${quantity(row.safe_stock)}，差额 ${stockDifference(row)}`" placement="top">
                <div class="stock-cell"><strong :class="stockClass(row)">{{ quantity(row.current_stock) }}</strong><span>/ {{ quantity(row.safe_stock) }}</span><small :class="stockClass(row)">{{ stockDifferenceLabel(row) }}</small></div>
              </el-tooltip>
            </template>
          </el-table-column>
          <el-table-column v-if="isColumnVisible('prices')" label="三档售价" min-width="220">
            <template #default="{ row }"><div class="price-stack"><span>零 {{ money(row.retail_price) }}</span><span>批 {{ money(row.wholesale_price) }}</span><span>VIP {{ money(row.vip_price) }}</span></div></template>
          </el-table-column>
          <el-table-column v-if="isColumnVisible('purchase')" label="参考进价" width="110"><template #default="{ row }">{{ money(row.purchase_price) }}</template></el-table-column>
          <el-table-column v-if="isColumnVisible('risk')" label="风险提示" min-width="150">
            <template #default="{ row }"><div class="risk-tags"><el-tag v-for="risk in productRisks(row)" :key="risk.label" :type="risk.type" size="small">{{ risk.label }}</el-tag><span v-if="!productRisks(row).length" class="muted">正常</span></div></template>
          </el-table-column>
          <el-table-column v-if="isColumnVisible('remark')" label="备注" min-width="150">
            <template #default="{ row }">
              <el-input v-if="isEditing(row, 'remark')" v-model="inlineEdit.value" size="small" autofocus @keyup.enter="confirmInlineEdit" @keyup.esc="cancelInlineEdit" @blur="cancelInlineEdit" />
              <span v-else class="editable-cell" title="双击编辑备注" @dblclick="startInlineEdit(row, 'remark')">{{ row.remark || '双击添加备注' }}</span>
            </template>
          </el-table-column>
          <el-table-column v-if="isColumnVisible('safeStock')" label="安全库存" width="125">
            <template #default="{ row }">
              <el-input-number v-if="isEditing(row, 'safe_stock')" v-model="inlineEdit.value" :min="0" controls-position="right" size="small" @keyup.enter="confirmInlineEdit" @keyup.esc="cancelInlineEdit" @blur="cancelInlineEdit" />
              <span v-else class="editable-cell" title="双击编辑安全库存" @dblclick="startInlineEdit(row, 'safe_stock')">{{ quantity(row.safe_stock) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" fixed="right" width="180">
            <template #default="{ row }"><el-button link type="primary" @click="openDialog(row)">编辑</el-button><el-button link type="primary" @click="moveProduct(row, -1)">上移</el-button><el-button link type="danger" @click="handleDelete(row)">停用</el-button></template>
          </el-table-column>
        </el-table>
      </div>

      <div v-else v-loading="loading" class="product-grid">
        <article v-for="row in orderedProducts" :key="row.id" class="product-card">
          <div class="product-card__header"><div><h3>{{ row.name }}</h3><p>{{ row.code || '自动编码' }} · {{ row.spec || '未填写规格' }}</p></div><el-tag size="small" effect="plain">{{ row.category_name || '未分类' }}</el-tag></div>
          <div class="product-card__metrics"><span><small>当前库存</small><strong :class="stockClass(row)">{{ quantity(row.current_stock) }}</strong></span><span><small>安全库存</small><strong>{{ quantity(row.safe_stock) }}</strong></span><span><small>库存差额</small><strong :class="stockClass(row)">{{ stockDifference(row) }}</strong></span></div>
          <div class="price-stack card-prices"><span>零售价 {{ money(row.retail_price) }}</span><span>批发价 {{ money(row.wholesale_price) }}</span><span>VIP价 {{ money(row.vip_price) }}</span></div>
          <div class="risk-tags"><el-tag v-for="risk in productRisks(row)" :key="risk.label" :type="risk.type" size="small">{{ risk.label }}</el-tag><span v-if="!productRisks(row).length" class="muted">库存状态正常</span></div>
          <div class="product-card__actions"><el-button link type="primary" @click="openDialog(row)">正式编辑</el-button><el-button link type="primary" @click="moveProduct(row, -1)">上移</el-button><el-button link type="danger" @click="handleDelete(row)">停用</el-button></div>
        </article>
        <el-empty v-if="!loading && !orderedProducts.length" description="暂无符合条件的商品" />
      </div>

      <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" class="archive-pagination" @size-change="loadData" @current-change="loadData" />
    </section>

    <el-dialog v-model="dialogVisible" :title="editingProduct ? '编辑商品档案' : '新增商品档案'" width="min(760px, 94vw)" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="102px" class="grouped-form">
        <section class="form-section"><h3>基础信息</h3><el-row :gutter="18"><el-col :xs="24" :sm="12"><el-form-item label="商品编码"><el-input v-model="form.code" placeholder="留空自动生成" /></el-form-item></el-col><el-col :xs="24" :sm="12"><el-form-item label="商品名称" prop="name"><el-input v-model="form.name" placeholder="请输入商品名称" /></el-form-item></el-col><el-col :xs="24" :sm="12"><el-form-item label="商品分类"><el-select v-model="form.category_id" placeholder="选择分类" style="width: 100%"><el-option v-for="cat in categories" :key="cat.id" :label="cat.name" :value="cat.id" /></el-select></el-form-item></el-col><el-col :xs="24" :sm="12"><el-form-item label="规格"><el-input v-model="form.spec" placeholder="如：500ml、10kg" /></el-form-item></el-col><el-col :xs="24" :sm="12"><el-form-item label="计量单位"><el-select v-model="form.unit" style="width: 100%"><el-option v-for="unit in units" :key="unit" :label="unit" :value="unit" /></el-select></el-form-item></el-col><el-col :xs="24" :sm="12"><el-form-item label="参考进价"><el-input-number v-model="form.purchase_price" :min="0" :precision="2" style="width: 100%" /></el-form-item></el-col></el-row></section>
        <section class="form-section"><h3>价格体系</h3><el-row :gutter="18"><el-col :xs="24" :sm="8"><el-form-item label="零售价"><el-input-number v-model="form.retail_price" :min="0" :precision="2" style="width: 100%" /></el-form-item></el-col><el-col :xs="24" :sm="8"><el-form-item label="批发价"><el-input-number v-model="form.wholesale_price" :min="0" :precision="2" style="width: 100%" /></el-form-item></el-col><el-col :xs="24" :sm="8"><el-form-item label="VIP价"><el-input-number v-model="form.vip_price" :min="0" :precision="2" style="width: 100%" /></el-form-item></el-col></el-row></section>
        <section class="form-section"><h3>库存安全配置</h3><el-row :gutter="18"><el-col :xs="24" :sm="12"><el-form-item label="安全库存"><el-input-number v-model="form.safe_stock" :min="0" style="width: 100%" /></el-form-item></el-col><el-col :xs="24" :sm="12"><el-form-item label="临期预警"><el-input-number v-model="form.stock_alert_days" :min="7" :max="365" style="width: 100%"><template #suffix>天</template></el-input-number></el-form-item></el-col></el-row><el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="3" /></el-form-item><el-form-item label="销售状态"><el-switch v-model="form.is_active" active-text="在售" inactive-text="停用" /></el-form-item></section>
      </el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="handleSave">保存商品</el-button></template>
    </el-dialog>

    <section class="page-card category-card"><div class="page-header"><div><p class="section-kicker">基础配置</p><h2>商品分类</h2></div><el-button plain @click="addCategory"><el-icon><Plus /></el-icon>添加分类</el-button></div><div class="category-list"><el-tag v-for="cat in categories" :key="cat.id" closable :type="getCategoryTagType(cat.id)" @close="handleDeleteCategory(cat.id)">{{ cat.name }}</el-tag><span v-if="!categories.length" class="muted">暂无分类</span></div></section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createCategory, createProduct, deleteCategory, deleteProduct, getCategories, getProducts, updateProduct } from '@/api'

const PREFERENCE_KEY = 'yingtai.products.workspace'
const optionalColumns = [
  { key: 'code', label: '编码' }, { key: 'category', label: '分类' }, { key: 'prices', label: '三档售价' },
  { key: 'purchase', label: '参考进价' }, { key: 'risk', label: '风险提示' }, { key: 'remark', label: '备注' }, { key: 'safeStock', label: '安全库存' }
]
const defaultVisibleColumns = optionalColumns.map(column => column.key)
const units = ['件', '箱', '袋', '瓶', '桶', '斤']
const loading = ref(false)
const saving = ref(false)
const loadError = ref('')
const products = ref([])
const categories = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const searchKeyword = ref('')
const filterCategory = ref(null)
const filterActive = ref(true)
const viewMode = ref('table')
const visibleColumns = ref([...defaultVisibleColumns])
const rowOrderIds = ref([])
const preferenceMessage = ref('')
const dialogVisible = ref(false)
const editingProduct = ref(null)
const formRef = ref(null)
const inlineEdit = reactive({ productId: null, field: '', value: null, original: null, session: 0 })

const defaultForm = () => ({ code: '', name: '', category_id: null, spec: '', unit: '件', purchase_price: 0, retail_price: 0, wholesale_price: 0, vip_price: 0, safe_stock: 0, stock_alert_days: 30, is_active: true, remark: '' })
const form = reactive(defaultForm())
const rules = { name: [{ required: true, message: '请输入商品名称', trigger: 'blur' }] }
const orderedProducts = computed(() => {
  const ranks = new Map(rowOrderIds.value.map((id, index) => [id, index]))
  return [...products.value].sort((left, right) => (ranks.get(left.id) ?? Number.MAX_SAFE_INTEGER) - (ranks.get(right.id) ?? Number.MAX_SAFE_INTEGER))
})

const number = value => Number(value || 0)
const quantity = value => number(value).toLocaleString('zh-CN', { maximumFractionDigits: 2 })
const money = value => `¥${number(value).toFixed(2)}`
const stockDifference = row => number(row.current_stock) - number(row.safe_stock)
const stockDifferenceLabel = row => stockDifference(row) >= 0 ? `高于安全线 ${quantity(stockDifference(row))}` : `缺口 ${quantity(Math.abs(stockDifference(row)))}`
const stockClass = row => number(row.current_stock) <= 0 ? 'danger-text' : stockDifference(row) < 0 ? 'warning-text' : 'success-text'
const productRisks = row => {
  const risks = []
  if (number(row.current_stock) <= 0) risks.push({ label: '缺货', type: 'danger' })
  else if (stockDifference(row) < 0) risks.push({ label: '低于安全库存', type: 'warning' })
  if (number(row.near_expiry_stock) > 0) risks.push({ label: `临期 ${quantity(row.near_expiry_stock)}`, type: 'danger' })
  return risks
}
const isColumnVisible = key => visibleColumns.value.includes(key)
const isEditing = (row, field) => inlineEdit.productId === row.id && inlineEdit.field === field
const isCurrentInlineEdit = (session, productId, field) => inlineEdit.session === session && inlineEdit.productId === productId && inlineEdit.field === field
const productPayload = product => ({ code: product.code || null, name: product.name, category_id: product.category_id ?? null, spec: product.spec || null, unit: product.unit || '件', retail_price: number(product.retail_price), wholesale_price: number(product.wholesale_price), vip_price: number(product.vip_price), purchase_price: number(product.purchase_price), safe_stock: Math.max(0, Math.round(number(product.safe_stock))), stock_alert_days: Math.max(7, Math.round(number(product.stock_alert_days) || 30)), is_active: Boolean(product.is_active), remark: product.remark || null })

const setPreferenceMessage = message => { preferenceMessage.value = message; window.setTimeout(() => { if (preferenceMessage.value === message) preferenceMessage.value = '' }, 2600) }
const restorePreferences = () => {
  try {
    const saved = JSON.parse(localStorage.getItem(PREFERENCE_KEY) || '{}')
    if (['table', 'card'].includes(saved.viewMode)) viewMode.value = saved.viewMode
    if (Array.isArray(saved.visibleColumns)) visibleColumns.value = saved.visibleColumns.filter(key => defaultVisibleColumns.includes(key))
    if (Array.isArray(saved.rowOrderIds)) rowOrderIds.value = saved.rowOrderIds.filter(Number.isFinite)
  } catch { localStorage.removeItem(PREFERENCE_KEY) }
}
const savePreferences = () => {
  localStorage.setItem(PREFERENCE_KEY, JSON.stringify({ viewMode: viewMode.value, visibleColumns: visibleColumns.value, rowOrderIds: rowOrderIds.value }))
  setPreferenceMessage('已保存本机的列表显示设置')
}
const resetPreferences = () => { viewMode.value = 'table'; visibleColumns.value = [...defaultVisibleColumns]; rowOrderIds.value = []; savePreferences() }
const moveProduct = (row, direction) => {
  const ids = orderedProducts.value.map(item => item.id)
  const index = ids.indexOf(row.id)
  const target = index + direction
  if (index < 0 || target < 0 || target >= ids.length) return ElMessage.info('已是当前页首尾商品')
  ;[ids[index], ids[target]] = [ids[target], ids[index]]
  rowOrderIds.value = [...new Set([...ids, ...rowOrderIds.value])]
  savePreferences()
}

const loadData = async () => {
  loading.value = true
  loadError.value = ''
  try {
    const data = await getProducts({ page: page.value, page_size: pageSize.value, keyword: searchKeyword.value || undefined, category_id: filterCategory.value || undefined, is_active: filterActive.value })
    products.value = data.items || []
    total.value = data.total || 0
  } catch { loadError.value = '商品列表加载失败，请检查网络后重试。' } finally { loading.value = false }
}
const reloadData = () => { page.value = 1; loadData() }
const loadCategories = async () => { try { categories.value = await getCategories() } catch { loadError.value = '商品分类加载失败，请稍后重试。' } }
const openDialog = product => { editingProduct.value = product || null; Object.assign(form, productPayload(product || defaultForm())); dialogVisible.value = true }
const handleSave = async () => {
  if (!formRef.value) return
  try { await formRef.value.validate() } catch { return }
  saving.value = true
  try {
    if (editingProduct.value) { await updateProduct(editingProduct.value.id, productPayload(form)); ElMessage.success('商品已更新') } else { await createProduct(productPayload(form)); ElMessage.success('商品已创建') }
    dialogVisible.value = false
    loadData()
  } catch { /* response interceptor provides the backend message */ } finally { saving.value = false }
}
const startInlineEdit = (row, field) => {
  if (!['remark', 'safe_stock'].includes(field)) return ElMessage.info('进价和售价请通过正式编辑保存，避免误操作。')
  inlineEdit.session += 1
  inlineEdit.productId = row.id
  inlineEdit.field = field
  inlineEdit.original = row[field] ?? (field === 'safe_stock' ? 0 : '')
  inlineEdit.value = inlineEdit.original
}
const cancelInlineEdit = () => {
  inlineEdit.session += 1
  Object.assign(inlineEdit, { productId: null, field: '', value: null, original: null })
}
const confirmInlineEdit = async () => {
  const row = products.value.find(product => product.id === inlineEdit.productId)
  if (!row || !['remark', 'safe_stock'].includes(inlineEdit.field)) return cancelInlineEdit()
  const editSession = inlineEdit.session
  const field = inlineEdit.field
  const nextValue = field === 'safe_stock' ? Math.max(0, Math.round(number(inlineEdit.value))) : String(inlineEdit.value || '').trim()
  if (row[field] === nextValue) return cancelInlineEdit()
  const previous = row[field]
  row[field] = nextValue
  try {
    await updateProduct(row.id, productPayload(row))
    ElMessage.success(field === 'safe_stock' ? '安全库存已更新' : '备注已更新')
  } catch {
    if (isCurrentInlineEdit(editSession, row.id, field)) row[field] = previous
  } finally {
    if (isCurrentInlineEdit(editSession, row.id, field)) cancelInlineEdit()
  }
}
const handleDelete = async row => {
  try { await ElMessageBox.confirm(`确定停用商品“${row.name}”吗？有库存的商品不能停用。`, '确认停用', { type: 'warning', confirmButtonText: '确认停用', cancelButtonText: '取消' }); await deleteProduct(row.id); ElMessage.success('商品已停用'); loadData() } catch { /* cancelled or request failed */ }
}
const addCategory = async () => {
  try { const { value } = await ElMessageBox.prompt('请输入分类名称', '添加商品分类', { inputPattern: /\S+/, inputErrorMessage: '分类名称不能为空', confirmButtonText: '保存', cancelButtonText: '取消' }); await createCategory({ name: value.trim(), sort_order: categories.value.length }); ElMessage.success('分类已添加'); loadCategories() } catch { /* cancelled or request failed */ }
}
const handleDeleteCategory = async id => { try { await ElMessageBox.confirm('确定删除此分类吗？分类下仍有商品时不能删除。', '确认删除', { type: 'warning' }); await deleteCategory(id); ElMessage.success('分类已删除'); loadCategories(); loadData() } catch { /* cancelled or request failed */ } }
const getCategoryTagType = id => ['', 'primary', 'success', 'warning', 'danger', 'info'][id % 6]

onMounted(() => { restorePreferences(); loadCategories(); loadData() })
</script>

<style scoped>
.archive-page { display: grid; gap: 20px; }
.archive-workspace { margin-bottom: 0; }
.section-kicker { color: var(--color-primary); font-size: 14px; font-weight: 600; margin-bottom: 5px; }
.section-description, .muted { color: var(--color-muted); font-size: 14px; margin-top: 6px; }
.archive-actions, .filter-bar, .product-card__actions, .category-list { align-items: center; display: flex; flex-wrap: wrap; gap: 10px; }
.view-mode :deep(.el-radio-button__inner), .archive-actions :deep(.el-button), .filter-bar :deep(.el-input__wrapper), .filter-bar :deep(.el-select__wrapper) { min-height: 42px; }
.filter-bar :deep(.el-input) { width: min(320px, 100%); }.filter-bar :deep(.el-select) { width: 180px; }
.preference-message { color: var(--color-success); font-size: 14px; margin: -8px 0 12px; }.archive-alert { margin-bottom: 14px; }
.archive-table-scroll { overflow-x: auto; }.data-table { min-width: 1280px; }.product-name, .stock-cell, .price-stack { display: grid; gap: 3px; }.product-name small, .stock-cell small { color: var(--color-muted); }.stock-cell { grid-template-columns: auto auto; }.stock-cell small { grid-column: 1 / -1; }.price-stack { color: var(--color-muted); font-size: 14px; }.risk-tags { align-items: center; display: flex; flex-wrap: wrap; gap: 5px; }.editable-cell { border-bottom: 1px dashed var(--color-primary); cursor: text; display: inline-block; min-width: 70px; padding: 5px 0; }.danger-text { color: var(--color-danger); }.warning-text { color: var(--color-warning); }.success-text { color: var(--color-success); }
.product-grid { display: grid; gap: 14px; grid-template-columns: repeat(auto-fit, minmax(275px, 1fr)); }.product-card { border: 1px solid var(--color-border); border-radius: 8px; display: grid; gap: 16px; padding: 18px; transition: box-shadow .18s ease, transform .18s ease; }.product-card:hover { box-shadow: 0 8px 18px rgba(29, 33, 41, .1); transform: translateY(-2px); }.product-card__header { align-items: start; display: flex; gap: 10px; justify-content: space-between; }.product-card h3 { font-size: 16px; }.product-card p { color: var(--color-muted); font-size: 14px; margin-top: 6px; }.product-card__metrics { display: grid; gap: 8px; grid-template-columns: repeat(3, 1fr); }.product-card__metrics span { display: grid; gap: 4px; }.product-card__metrics small { color: var(--color-muted); font-size: 14px; }.product-card__metrics strong { font-size: 16px; }.card-prices { border-bottom: 1px solid var(--color-border); border-top: 1px solid var(--color-border); padding: 10px 0; }.archive-pagination { justify-content: flex-end; margin-top: 20px; }.category-card { margin-bottom: 0; }.category-list :deep(.el-tag) { font-size: 14px; min-height: 34px; padding: 0 10px; }
.column-panel { display: grid; gap: 12px; }.column-panel :deep(.el-checkbox-group) { display: grid; gap: 9px; }.form-section { border-bottom: 1px solid var(--color-border); margin-bottom: 20px; padding-bottom: 4px; }.form-section:last-child { border-bottom: 0; margin-bottom: 0; }.form-section h3 { font-size: 16px; margin-bottom: 16px; }
@media (max-width: 780px) { .page-header { align-items: flex-start; flex-direction: column; gap: 14px; }.archive-actions { width: 100%; }.filter-bar :deep(.el-input), .filter-bar :deep(.el-select) { width: 100%; }.product-card__metrics { grid-template-columns: 1fr; } }
@media (prefers-reduced-motion: reduce) { .product-card { transition: none; }.product-card:hover { transform: none; } }
</style>
