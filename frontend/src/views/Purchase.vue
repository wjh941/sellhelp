<template>
  <div>
    <div class="page-card">
      <div class="page-header">
        <h2>入库开单</h2>
        <div class="actions">
          <el-button type="primary" @click="openCreateDialog()">
            <el-icon><Plus /></el-icon>新建入库单
          </el-button>
        </div>
      </div>

      <div class="search-bar">
        <el-date-picker v-model="filterDate" type="daterange" range-separator="至"
          start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" />
        <el-select v-model="filterSupplier" placeholder="供应商" style="width: 180px;" clearable>
          <el-option v-for="s in suppliers" :key="s.id" :label="s.name" :value="s.id" />
        </el-select>
        <el-button type="primary" @click="loadData">查询</el-button>
      </div>

      <el-table :data="orders" stripe v-loading="loading">
        <el-table-column prop="order_no" label="入库单号" width="200" />
        <el-table-column prop="supplier_name" label="供应商" min-width="150" />
        <el-table-column label="入库日期" width="160">
          <template #default="{ row }">{{ formatDate(row.purchase_date) }}</template>
        </el-table-column>
        <el-table-column prop="total_amount" label="入库金额" width="120">
          <template #default="{ row }">
            <span style="color: #409EFF; font-weight: bold;">¥{{ row.total_amount }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="operator" label="操作员" width="100" />
        <el-table-column prop="remark" label="备注" min-width="150" show-overflow-tooltip />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" link @click="viewDetail(row)">查看</el-button>
            <el-button type="danger" size="small" link @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 新建入库单 -->
    <el-dialog v-model="createDialogVisible" title="新建入库单" width="900px" top="5vh">
      <el-form :model="newOrder" label-width="100px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="供应商" required>
              <el-select v-model="newOrder.supplier_id" placeholder="选择供应商" style="width: 100%;">
                <el-option v-for="s in suppliers" :key="s.id" :label="s.name" :value="s.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="采购日期">
              <el-date-picker v-model="newOrder.purchase_date" type="datetime"
                placeholder="选择日期" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%;" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="操作员">
          <el-input v-model="newOrder.operator" placeholder="操作员姓名" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="newOrder.remark" type="textarea" :rows="2" />
        </el-form-item>

        <el-divider content-position="left">入库商品明细</el-divider>

        <div style="margin-bottom: 10px;">
          <el-button type="primary" size="small" @click="addItem">
            <el-icon><Plus /></el-icon>添加商品
          </el-button>
        </div>

        <el-table :data="newOrder.items" border size="small" style="width: 100%;" empty-text="请添加入库商品">
          <el-table-column label="商品" width="200">
            <template #default="{ row, $index }">
              <el-select v-model="row.product_id" placeholder="选择商品" filterable style="width: 100%;">
                <el-option v-for="p in products" :key="p.id" :label="p.name" :value="p.id" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column prop="batch_no" label="批次号" width="140">
            <template #default="{ row }">
              <el-input v-model="row.batch_no" size="small" />
            </template>
          </el-table-column>
          <el-table-column label="生产日期" width="140">
            <template #default="{ row }">
              <el-date-picker v-model="row.production_date" type="date" placeholder="日期"
                value-format="YYYY-MM-DD" size="small" style="width: 100%;" />
            </template>
          </el-table-column>
          <el-table-column label="到期日期" width="140">
            <template #default="{ row }">
              <el-date-picker v-model="row.expiry_date" type="date" placeholder="日期"
                value-format="YYYY-MM-DD" size="small" style="width: 100%;" />
            </template>
          </el-table-column>
          <el-table-column label="数量" width="100">
            <template #default="{ row }">
              <el-input-number v-model="row.quantity" :min="0" size="small" style="width: 100%;" />
            </template>
          </el-table-column>
          <el-table-column label="单价" width="100">
            <template #default="{ row }">
              <el-input-number v-model="row.unit_price" :min="0" :precision="2" size="small" style="width: 100%;" />
            </template>
          </el-table-column>
          <el-table-column label="金额" width="100">
            <template #default="{ row }">
              <strong>¥{{ (row.quantity * row.unit_price).toFixed(2) }}</strong>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="70">
            <template #default="{ $index }">
              <el-button type="danger" size="small" link @click="removeItem($index)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div style="text-align: right; margin-top: 15px;">
          <span>合计金额：</span>
          <span style="font-size: 20px; color: #409EFF; font-weight: bold;">¥{{ totalAmount.toFixed(2) }}</span>
        </div>
      </el-form>

      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitOrder" :disabled="!newOrder.items.length">
          确认入库
        </el-button>
      </template>
    </el-dialog>

    <!-- 入库单详情 -->
    <el-dialog v-model="detailVisible" title="入库单详情" width="700px">
      <el-descriptions :column="2" border v-if="currentOrder">
        <el-descriptions-item label="入库单号">{{ currentOrder.order_no }}</el-descriptions-item>
        <el-descriptions-item label="供应商">{{ currentOrder.supplier_name }}</el-descriptions-item>
        <el-descriptions-item label="入库日期">{{ formatDate(currentOrder.purchase_date) }}</el-descriptions-item>
        <el-descriptions-item label="操作员">{{ currentOrder.operator }}</el-descriptions-item>
        <el-descriptions-item label="入库金额" :span="2">
          <span style="color: #409EFF; font-weight: bold;">¥{{ currentOrder.total_amount }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="备注" :span="2">{{ currentOrder.remark || '-' }}</el-descriptions-item>
      </el-descriptions>

      <el-divider>商品明细</el-divider>

      <el-table :data="currentOrder?.items || []" border size="small">
        <el-table-column prop="product_name" label="商品" min-width="150" />
        <el-table-column prop="batch_no" label="批次号" width="120" />
        <el-table-column prop="quantity" label="数量" width="80" />
        <el-table-column prop="unit_price" label="单价" width="80">
          <template #default="{ row }">¥{{ row.unit_price }}</template>
        </el-table-column>
        <el-table-column prop="amount" label="金额" width="100">
          <template #default="{ row }">¥{{ row.amount }}</template>
        </el-table-column>
        <el-table-column label="剩余库存" width="100">
          <template #default="{ row }">
            <el-tag :type="row.remaining_quantity > 0 ? 'success' : 'info'" size="small">
              {{ row.remaining_quantity }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getSuppliers, getProducts, getPurchaseOrders, createPurchaseOrder, deletePurchaseOrder, getPurchaseOrder
} from '@/api'

const loading = ref(false)
const orders = ref([])
const suppliers = ref([])
const products = ref([])
const filterDate = ref([])
const filterSupplier = ref(null)

const createDialogVisible = ref(false)
const detailVisible = ref(false)
const currentOrder = ref(null)

const defaultItem = () => ({
  product_id: null, batch_no: '', production_date: null,
  expiry_date: null, quantity: 0, unit_price: 0, remark: ''
})

const newOrder = reactive({
  supplier_id: null, purchase_date: null, operator: '', remark: '',
  items: [defaultItem()]
})

const totalAmount = computed(() => {
  return newOrder.items.reduce((sum, item) => sum + item.quantity * item.unit_price, 0)
})

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const loadData = async () => {
  loading.value = true
  try {
    const params = {}
    if (filterDate.value?.length === 2) {
      params.start_date = filterDate.value[0]
      params.end_date = filterDate.value[1]
    }
    if (filterSupplier.value) {
      params.supplier_id = filterSupplier.value
    }
    orders.value = await getPurchaseOrders(params)
  } finally {
    loading.value = false
  }
}

const loadSuppliers = async () => {
  suppliers.value = await getSuppliers()
}

const loadProducts = async () => {
  const data = await getProducts({ page_size: 200, is_active: true })
  products.value = data.items || []
}

const openCreateDialog = () => {
  Object.assign(newOrder, {
    supplier_id: null, purchase_date: new Date().toISOString().slice(0, 19),
    operator: '', remark: '', items: [defaultItem()]
  })
  createDialogVisible.value = true
}

const addItem = () => {
  newOrder.items.push(defaultItem())
}

const removeItem = (index) => {
  if (newOrder.items.length > 1) {
    newOrder.items.splice(index, 1)
  } else {
    ElMessage.warning('至少保留一条明细')
  }
}

const submitOrder = async () => {
  if (!newOrder.supplier_id) {
    ElMessage.warning('请选择供应商')
    return
  }
  // 过滤掉未选择商品的行
  const validItems = newOrder.items.filter(i => i.product_id)
  if (!validItems.length) {
    ElMessage.warning('请至少添加一条商品')
    return
  }

  try {
    await createPurchaseOrder({
      supplier_id: newOrder.supplier_id,
      purchase_date: newOrder.purchase_date,
      operator: newOrder.operator,
      remark: newOrder.remark,
      items: validItems
    })
    ElMessage.success('入库成功')
    createDialogVisible.value = false
    loadData()
  } catch (e) { /* handled */ }
}

const viewDetail = async (row) => {
  currentOrder.value = await getPurchaseOrder(row.id)
  detailVisible.value = true
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除入库单"${row.order_no}"？`, '确认', { type: 'warning' })
    await deletePurchaseOrder(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch { /* cancelled */ }
}

onMounted(async () => {
  await Promise.all([loadSuppliers(), loadProducts()])
  loadData()
})
</script>
