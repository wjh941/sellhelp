<template>
  <div>
    <div class="page-card">
      <div class="page-header">
        <h2>销售开单</h2>
        <div class="actions">
          <el-button type="primary" @click="openCreateDialog()">
            <el-icon><Plus /></el-icon>新建销售单
          </el-button>
        </div>
      </div>

      <div class="search-bar">
        <el-date-picker v-model="filterDate" type="daterange" range-separator="至"
          start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" />
        <el-select v-model="filterCustomer" placeholder="客户" style="width: 180px;" clearable>
          <el-option v-for="c in customers" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
        <el-select v-model="filterPayment" placeholder="结算方式" style="width: 120px;" clearable>
          <el-option label="现结" value="现结" />
          <el-option label="赊账" value="赊账" />
          <el-option label="部分结账" value="部分结账" />
        </el-select>
        <el-button type="primary" @click="loadData">查询</el-button>
      </div>

      <el-table :data="orders" stripe v-loading="loading">
        <el-table-column prop="order_no" label="销售单号" width="200" />
        <el-table-column prop="customer_name" label="客户" min-width="150">
          <template #default="{ row }">
            {{ row.customer_name }}
            <el-tag v-if="row.price_level_used" size="small" style="margin-left: 5px;">
              {{ row.price_level_used }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="销售日期" width="160">
          <template #default="{ row }">{{ formatDate(row.sale_date) }}</template>
        </el-table-column>
        <el-table-column prop="total_amount" label="订单金额" width="110">
          <template #default="{ row }">¥{{ row.total_amount }}</template>
        </el-table-column>
        <el-table-column prop="final_amount" label="实收金额" width="110">
          <template #default="{ row }">
            <span style="color: #409EFF; font-weight: bold;">¥{{ row.final_amount }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="payment_type" label="结算方式" width="100">
          <template #default="{ row }">
            <el-tag :type="row.payment_type === '现结' ? 'success' : 'warning'" size="small">
              {{ row.payment_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="debt_amount" label="欠款" width="100">
          <template #default="{ row }">
            <span :class="row.debt_amount > 0 ? 'tag-danger' : ''">¥{{ row.debt_amount }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" link @click="viewDetail(row)">查看</el-button>
            <el-button v-if="row.payment_type !== '现结'" type="success" size="small" link @click="handlePay(row)">收款</el-button>
            <el-button type="danger" size="small" link @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 新建销售单 -->
    <el-dialog v-model="createDialogVisible" title="新建销售单（FIFO先进先出）" width="950px" top="3vh">
      <el-form :model="newOrder" label-width="100px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="选择客户" required>
              <el-select v-model="newOrder.customer_id" placeholder="选择客户" style="width: 100%;"
                @change="onCustomerChange">
                <el-option v-for="c in customers" :key="c.id" :label="c.name" :value="c.id">
                  <span>{{ c.name }}</span>
                  <el-tag v-if="c.is_vip" type="danger" size="small" style="margin-left: 5px;">VIP</el-tag>
                </el-option>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="价格档次">
              <el-tag v-if="currentCustomer">
                {{ currentCustomer.is_vip ? '大客户价' : currentCustomer.customer_type === '散户' ? '零售价' : '批发价' }}
              </el-tag>
              <span v-else style="color: #909399;">选择客户后自动匹配</span>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="销售日期">
          <el-date-picker v-model="newOrder.sale_date" type="datetime"
            placeholder="选择日期" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="操作员">
          <el-input v-model="newOrder.operator" placeholder="操作员姓名" />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="结算方式" required>
              <el-radio-group v-model="newOrder.payment_type">
                <el-radio value="现结">现结</el-radio>
                <el-radio value="赊账">赊账</el-radio>
                <el-radio value="部分结账">部分结账</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="12" v-if="newOrder.payment_type === '部分结账'">
            <el-form-item label="已收金额" required>
              <el-input-number v-model="newOrder.paid_amount" :min="0" :precision="2" style="width: 100%;" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="备注">
          <el-input v-model="newOrder.remark" type="textarea" :rows="2" />
        </el-form-item>

        <el-divider content-position="left">商品明细（系统将自动按FIFO先进先出分配批次）</el-divider>

        <div style="margin-bottom: 10px;">
          <el-button type="primary" size="small" @click="addItem">
            <el-icon><Plus /></el-icon>添加商品
          </el-button>
          <el-button size="small" @click="batchAdd" style="margin-left: 10px;">快速批量添加</el-button>
        </div>

        <el-table :data="newOrder.items" border size="small" style="width: 100%;" empty-text="请添加销售商品">
          <el-table-column label="商品" width="200">
            <template #default="{ row }">
              <el-select v-model="row.product_id" placeholder="搜索商品" filterable style="width: 100%;"
                @change="onProductChange(row)">
                <el-option v-for="p in products" :key="p.id" :label="p.name" :value="p.id">
                  <span>{{ p.name }}</span>
                  <span style="float: right; color: #909399;">库存:{{ p.current_stock }}</span>
                </el-option>
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="库存提示" width="120">
            <template #default="{ row }">
              <span v-if="row.product_info" :class="getStockClass(row.product_info.current_stock)">
                库存: {{ row.product_info.current_stock }}
              </span>
              <span v-else style="color: #909399;">-</span>
            </template>
          </el-table-column>
          <el-table-column label="数量" width="100">
            <template #default="{ row }">
              <el-input-number v-model="row.quantity" :min="0" size="small" style="width: 100%;"
                @change="calculateItemPrice(row)" />
            </template>
          </el-table-column>
          <el-table-column label="单价" width="100">
            <template #default="{ row }">
              <el-input-number v-model="row.unit_price" :min="0" :precision="2" size="small"
                style="width: 100%;" @change="calculateItemPrice(row)" />
            </template>
          </el-table-column>
          <el-table-column label="成本价" width="90">
            <template #default="{ row }">
              <span style="color: #909399;">¥{{ row.cost_price?.toFixed(2) || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="利润" width="100">
            <template #default="{ row }">
              <span style="color: #67C23A;">¥{{ calcProfit(row).toFixed(2) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="金额" width="100">
            <template #default="{ row }">
              <strong>¥{{ calcAmount(row).toFixed(2) }}</strong>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="70">
            <template #default="{ $index }">
              <el-button type="danger" size="small" link @click="removeItem($index)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div style="text-align: right; margin-top: 15px; display: flex; justify-content: flex-end; gap: 30px;">
          <div>订单金额：<strong>¥{{ totalAmount.toFixed(2) }}</strong></div>
          <div>预计利润：<strong style="color: #67C23A;">¥{{ totalProfit.toFixed(2) }}</strong></div>
        </div>
      </el-form>

      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitOrder" :disabled="!newOrder.items.length">
          确认开单
        </el-button>
      </template>
    </el-dialog>

    <!-- 销售单详情 -->
    <el-dialog v-model="detailVisible" title="销售单详情" width="800px">
      <el-descriptions :column="3" border v-if="currentOrder">
        <el-descriptions-item label="销售单号" :span="2">{{ currentOrder.order_no }}</el-descriptions-item>
        <el-descriptions-item label="客户">{{ currentOrder.customer_name }}</el-descriptions-item>
        <el-descriptions-item label="销售日期" :span="2">{{ formatDate(currentOrder.sale_date) }}</el-descriptions-item>
        <el-descriptions-item label="价格档次">{{ currentOrder.price_level_used }}</el-descriptions-item>
        <el-descriptions-item label="订单金额">¥{{ currentOrder.total_amount }}</el-descriptions-item>
        <el-descriptions-item label="实收金额">
          <span style="color: #409EFF; font-weight: bold;">¥{{ currentOrder.final_amount }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="结算方式">{{ currentOrder.payment_type }}</el-descriptions-item>
      </el-descriptions>

      <el-divider>商品明细（含FIFO批次出库）</el-divider>

      <el-table :data="currentOrder?.items || []" border size="small">
        <el-table-column prop="product_name" label="商品" min-width="150" />
        <el-table-column prop="quantity" label="数量" width="80" />
        <el-table-column prop="unit_price" label="售价" width="80">
          <template #default="{ row }">¥{{ row.unit_price }}</template>
        </el-table-column>
        <el-table-column prop="cost_price" label="成本" width="80">
          <template #default="{ row }">¥{{ row.cost_price }}</template>
        </el-table-column>
        <el-table-column prop="profit" label="利润" width="90">
          <template #default="{ row }">
            <span style="color: #67C23A;">¥{{ row.profit }}</span>
          </template>
        </el-table-column>
        <el-table-column label="批次" min-width="200">
          <template #default="{ row }">
            <div v-for="b in (row.batches_used || [])" :key="b.batch_id" style="font-size: 12px;">
              <el-tag size="small" style="margin-right: 4px;">{{ b.batch_no }}</el-tag>
              × {{ b.quantity }} @¥{{ b.unit_cost }}
            </div>
            <span v-if="!row.batches_used || row.batches_used.length === 0">-</span>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 收款对话框 -->
    <el-dialog v-model="payDialogVisible" title="收款" width="400px">
      <el-form :model="payForm" label-width="80px">
        <el-form-item label="订单金额">
          <span>¥{{ payOrder?.final_amount }}</span>
        </el-form-item>
        <el-form-item label="已收金额">
          <span>¥{{ payOrder?.paid_amount }}</span>
        </el-form-item>
        <el-form-item label="未收金额">
          <span class="tag-danger">¥{{ (payOrder?.final_amount || 0) - (payOrder?.paid_amount || 0) }}</span>
        </el-form-item>
        <el-form-item label="收款方式">
          <el-radio-group v-model="payForm.payment_type">
            <el-radio value="现结">现结（全额收款）</el-radio>
            <el-radio value="部分结账">部分结账</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="payForm.payment_type === '部分结账'" label="收款金额">
          <el-input-number v-model="payForm.paid_amount" :min="0"
            :max="(payOrder?.final_amount || 0) - (payOrder?.paid_amount || 0)"
            :precision="2" style="width: 100%;" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="payDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmPay">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getCustomers, getProducts, getSalesOrders, createSalesOrder, getSalesOrder,
  deleteSalesOrder, updatePayment
} from '@/api'

const loading = ref(false)
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

const currentCustomer = computed(() => {
  return customers.value.find(c => c.id === newOrder.customer_id)
})

const defaultItem = () => ({
  product_id: null, product_info: null, quantity: 0,
  unit_price: 0, cost_price: 0, remark: ''
})

const newOrder = reactive({
  customer_id: null, sale_date: null, operator: '', remark: '',
  payment_type: '现结', paid_amount: 0,
  items: [defaultItem()]
})

const totalAmount = computed(() => {
  return newOrder.items.reduce((sum, item) => sum + calcAmount(item), 0)
})

const totalProfit = computed(() => {
  return newOrder.items.reduce((sum, item) => sum + calcProfit(item), 0)
})

const calcAmount = (row) => row.quantity * row.unit_price
const calcProfit = (row) => (row.unit_price - row.cost_price) * row.quantity

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const getStockClass = (stock) => {
  if (stock <= 0) return 'tag-danger'
  if (stock < 10) return 'tag-warning'
  return 'tag-success'
}

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

const loadCustomers = async () => {
  customers.value = await getCustomers()
}

const loadProducts = async () => {
  const data = await getProducts({ page_size: 500, is_active: true })
  products.value = data.items || []
}

const openCreateDialog = () => {
  Object.assign(newOrder, {
    customer_id: null, sale_date: new Date().toISOString().slice(0, 19),
    operator: '', remark: '',
    payment_type: '现结', paid_amount: 0,
    items: [defaultItem()]
  })
  createDialogVisible.value = true
}

const onCustomerChange = () => {
  // 客户变更时，重新计算所有商品的价格
  newOrder.items.forEach(item => {
    if (item.product_id) {
      calculateItemPrice(item)
    }
  })
}

const onProductChange = (row) => {
  const product = products.value.find(p => p.id === row.product_id)
  if (product) {
    row.product_info = product
    // 自动匹配价格
    if (currentCustomer.value) {
      if (currentCustomer.value.is_vip) {
        row.unit_price = product.vip_price || product.wholesale_price || product.retail_price
      } else if (currentCustomer.value.customer_type === '散户') {
        row.unit_price = product.retail_price
      } else {
        row.unit_price = product.wholesale_price
      }
    }
    // 获取成本价（简单估算，实际会在后端FIFO计算）
    row.cost_price = product.purchase_price || 0
  }
}

const calculateItemPrice = (row) => {
  // 价格已在onProductChange中设置
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
  if (!newOrder.customer_id) {
    ElMessage.warning('请选择客户')
    return
  }
  const validItems = newOrder.items.filter(i => i.product_id && i.quantity > 0)
  if (!validItems.length) {
    ElMessage.warning('请添加商品')
    return
  }

  try {
    const submitData = {
      customer_id: newOrder.customer_id,
      sale_date: newOrder.sale_date,
      operator: newOrder.operator,
      remark: newOrder.remark,
      payment_type: newOrder.payment_type,
      items: validItems.map(i => ({
        product_id: i.product_id,
        quantity: i.quantity,
        unit_price: i.unit_price
      }))
    }

    if (newOrder.payment_type === '部分结账') {
      submitData.paid_amount = newOrder.paid_amount
    }

    await createSalesOrder(submitData)
    ElMessage.success('开单成功，库存已按FIFO扣减')
    createDialogVisible.value = false
    loadData()
  } catch (e) {
    // error handled
  }
}

const viewDetail = async (row) => {
  currentOrder.value = await getSalesOrder(row.id)
  detailVisible.value = true
}

const handlePay = (row) => {
  payOrder.value = row
  Object.assign(payForm, {
    payment_type: '现结',
    paid_amount: row.final_amount - row.paid_amount
  })
  payDialogVisible.value = true
}

const payForm = reactive({
  payment_type: '现结',
  paid_amount: 0
})

const confirmPay = async () => {
  try {
    await updatePayment(payOrder.value.id, {
      payment_type: payForm.payment_type,
      paid_amount: payForm.paid_amount
    })
    ElMessage.success('收款成功')
    payDialogVisible.value = false
    loadData()
  } catch (e) { /* handled */ }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除销售单"${row.order_no}"？\n库存将自动冲回！`, '确认', { type: 'warning' })
    await deleteSalesOrder(row.id)
    ElMessage.success('删除成功，库存已冲回')
    loadData()
  } catch { /* cancelled */ }
}

onMounted(async () => {
  await Promise.all([loadCustomers(), loadProducts()])
  loadData()
})
</script>
