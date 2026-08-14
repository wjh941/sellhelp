<template>
  <div>
    <div class="page-card">
      <div class="page-header">
        <h2>退货管理</h2>
        <div class="actions">
          <el-button type="primary" @click="openCreateDialog('客户退货')">
            <el-icon><Plus /></el-icon>客户退货
          </el-button>
          <el-button type="warning" @click="openCreateDialog('供应商退货')">
            <el-icon><RefreshLeft /></el-icon>供应商退货
          </el-button>
          <el-button @click="openStockTakeDialog">
            <el-icon><EditPen /></el-icon>库存盘点
          </el-button>
        </div>
      </div>

      <div class="search-bar">
        <el-select v-model="filterType" placeholder="退货类型" style="width: 150px;" clearable>
          <el-option label="客户退货" value="客户退货" />
          <el-option label="供应商退货" value="供应商退货" />
        </el-select>
        <el-date-picker v-model="filterDate" type="daterange" range-separator="至"
          start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" />
        <el-button type="primary" @click="loadReturns">查询</el-button>
      </div>

      <el-table :data="returns" stripe v-loading="loading">
        <el-table-column prop="order_no" label="退货单号" width="180" />
        <el-table-column prop="return_type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.return_type === '客户退货' ? 'warning' : 'danger'" size="small">
              {{ row.return_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="product_name" label="商品" min-width="150" />
        <el-table-column prop="quantity" label="退货数量" width="100" />
        <el-table-column prop="refund_amount" label="退款金额" width="110">
          <template #default="{ row }">¥{{ row.refund_amount }}</template>
        </el-table-column>
        <el-table-column prop="reason" label="退货原因" min-width="200" show-overflow-tooltip />
        <el-table-column prop="created_at" label="操作时间" width="160">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="operator" label="操作员" width="100" />
      </el-table>
    </div>

    <!-- 新建退货单 -->
    <el-dialog v-model="createDialogVisible" :title="dialogTitle" width="600px">
      <el-form :model="returnForm" label-width="100px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="退货类型">
              <el-tag :type="returnForm.return_type === '客户退货' ? 'warning' : 'danger'">
                {{ returnForm.return_type }}
              </el-tag>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="关联单号">
              <el-input v-model="returnForm.related_order_no" placeholder="原销售单/入库单号（可选）" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="选择商品" required>
          <el-select v-model="returnForm.product_id" placeholder="选择商品" filterable style="width: 100%;"
            @change="onProductChange">
            <el-option v-for="p in products" :key="p.id" :label="p.name" :value="p.id">
              <span>{{ p.name }}</span>
              <span v-if="p.current_stock !== undefined" style="float: right; color: #909399;">库存:{{ p.current_stock }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item v-if="productStockInfo.batches?.length" label="选择批次">
          <el-select v-model="returnForm.batch_id" placeholder="选择批次（可选）" style="width: 100%;">
            <el-option v-for="b in productStockInfo.batches" :key="b.batch_id"
              :label="`${b.batch_no} - 剩余${b.remaining}`" :value="b.batch_id">
              <span>{{ b.batch_no }}</span>
              <span style="float: right; color: #909399;">剩余: {{ b.remaining }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="退货数量" required>
              <el-input-number v-model="returnForm.quantity" :min="0" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col v-if="returnForm.return_type !== customerReturnType" :span="12">
            <el-form-item label="退款金额">
              <el-input-number v-model="returnForm.refund_amount" :min="0" :precision="2" style="width: 100%;" />
              <el-input-number v-if="returnForm.return_type === '渚涔ュ簲鍟嗛€€璐?'" v-model="returnForm.refund_amount" :min="0" :precision="2" style="width: 100%;" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="退货原因">
          <el-input v-model="returnForm.reason" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="操作员">
          <el-input v-model="returnForm.operator" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitReturn">确认退货</el-button>
      </template>
    </el-dialog>

    <!-- 盘点对话框 -->
    <el-dialog v-model="stockTakeVisible" title="库存盘点" width="900px" top="5vh">
      <el-alert type="info" :closable="false" style="margin-bottom: 15px;">
        系统已自动导入当前库存数据，请对照实际盘点数量填写。
      </el-alert>

      <div style="max-height: 500px; overflow-y: auto;">
        <el-table :data="stockTakeItems" border size="small">
          <el-table-column prop="product_name" label="商品" min-width="150" />
          <el-table-column prop="batch_no" label="批次" width="130" />
          <el-table-column prop="system_quantity" label="系统数量" width="100" />
          <el-table-column label="实际数量" width="120">
            <template #default="{ row }">
              <el-input-number v-model="row.actual_quantity" :min="0" size="small" style="width: 100%;" />
            </template>
          </el-table-column>
          <el-table-column label="差异" width="100">
            <template #default="{ row }">
              <span :class="row.actual_quantity - row.system_quantity > 0 ? 'tag-success' : 
                row.actual_quantity - row.system_quantity < 0 ? 'tag-danger' : ''">
                {{ row.actual_quantity - row.system_quantity }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="差异金额" width="110">
            <template #default="{ row }">
              <span style="color: #606266;">
                ¥{{ ((row.actual_quantity - row.system_quantity) * (row.unit_price || 0)).toFixed(2) }}
              </span>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <template #footer>
        <el-button @click="stockTakeVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmStockTakeAction">确认盘点结果</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getReturns, createReturn, prepareStockTake, confirmStockTake as confirmStockTakeApi, getProducts, getProductStock
} from '@/api'

const loading = ref(false)
const returns = ref([])
const products = ref([])
const filterType = ref('')
const filterDate = ref([])

const createDialogVisible = ref(false)
const stockTakeVisible = ref(false)
const stockTakeItems = ref([])
const currentReturnType = ref('客户退货')
const productStockInfo = ref({ batches: [] })

const returnForm = reactive({
  return_type: '客户退货', related_order_no: '', product_id: null,
  batch_id: null, quantity: 0, refund_amount: 0, reason: '', operator: ''
})

const customerReturnType = returnForm.return_type
const dialogTitle = () => `${currentReturnType.value}`

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const loadReturns = async () => {
  loading.value = true
  try {
    const params = {}
    if (filterType.value) params.return_type = filterType.value
    if (filterDate.value?.length === 2) {
      params.start_date = filterDate.value[0]
      params.end_date = filterDate.value[1]
    }
    returns.value = await getReturns(params)
  } finally {
    loading.value = false
  }
}

const loadProducts = async () => {
  const data = await getProducts({ page_size: 500, is_active: true })
  products.value = data.items || []
}

const openCreateDialog = (type) => {
  currentReturnType.value = type
  Object.assign(returnForm, {
    return_type: type, related_order_no: '', product_id: null,
    batch_id: null, quantity: 0, refund_amount: 0, reason: '', operator: ''
  })
  productStockInfo.value = { batches: [] }
  createDialogVisible.value = true
}

const onProductChange = async () => {
  if (returnForm.product_id) {
    const stock = await getProductStock(returnForm.product_id)
    productStockInfo.value = stock
    // 自动填入第一个批次
    if (stock.batches?.length) {
      returnForm.batch_id = stock.batches[0].batch_id
    }
  }
}

const submitReturn = async () => {
  if (returnForm.return_type === customerReturnType && !returnForm.related_order_no.trim()) {
    ElMessage.warning('Source sales order is required')
    return
  }
  if (returnForm.return_type === '瀹㈡埛閫€璐?' && !returnForm.related_order_no.trim()) {
    ElMessage.warning('璇疯緭鍏ュ師閿€鍞崟鍙?')
    return
  }
  if (!returnForm.product_id) {
    ElMessage.warning('请选择商品')
    return
  }
  try {
    await createReturn(returnForm)
    ElMessage.success('退货成功，库存已更新')
    createDialogVisible.value = false
    loadReturns()
  } catch (e) { /* handled */ }
}

const openStockTakeDialog = async () => {
  try {
    const items = await prepareStockTake()
    stockTakeItems.value = items.map(item => ({
      ...item,
      actual_quantity: item.system_quantity
    }))
    stockTakeVisible.value = true
  } catch (e) { /* handled */ }
}

const confirmStockTakeAction = async () => {
  try {
    await ElMessageBox.confirm(`确认盘点结果？系统将自动调整库存。`, '确认', { type: 'warning' })
    const items = stockTakeItems.value.map(item => ({
      product_id: item.product_id,
      batch_id: item.batch_id,
      actual_quantity: item.actual_quantity,
      reason: ''
    }))
    await confirmStockTakeApi(items)
    ElMessage.success('盘点完成')
    stockTakeVisible.value = false
  } catch { /* cancelled */ }
}

onMounted(async () => {
  await loadProducts()
  loadReturns()
})
</script>
