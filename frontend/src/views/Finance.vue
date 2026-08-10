<template>
  <div>
    <div class="page-card">
      <div class="page-header">
        <h2>💰 客户回款管理</h2>
        <div class="actions">
          <el-button @click="loadData">刷新</el-button>
          <el-button type="success" @click="openBatchRepay">批量还款</el-button>
        </div>
      </div>

      <el-row :gutter="16" class="stat-row">
        <el-col :span="6">
          <div class="stat-card blue">
            <div class="stat-value">¥{{ formatMoney(totalDebt) }}</div>
            <div class="stat-label">欠款总额</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card orange">
            <div class="stat-value">{{ debtCustomers.length }}</div>
            <div class="stat-label">欠款客户数</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card red">
            <div class="stat-value">{{ overdueCount }}</div>
            <div class="stat-label">超期客户数</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card green">
            <div class="stat-value">¥{{ formatMoney(repaidToday) }}</div>
            <div class="stat-label">今日回款</div>
          </div>
        </el-col>
      </el-row>

      <div class="search-bar">
        <el-select v-model="filterType" placeholder="客户类型" style="width: 140px;" clearable>
          <el-option label="散户" value="散户" />
          <el-option label="小店" value="小店" />
          <el-option label="工厂" value="工厂" />
          <el-option label="食堂" value="食堂" />
          <el-option label="VIP" value="VIP" />
        </el-select>
        <el-button type="primary" @click="loadData">查询</el-button>
      </div>

      <el-table :data="debtCustomers" stripe v-loading="loading">
        <el-table-column prop="name" label="客户名称" min-width="120">
          <template #default="{ row }">
            {{ row.name }}
            <el-tag v-if="row.is_vip" type="danger" size="small" style="margin-left: 4px;">VIP</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="type" label="类型" width="80">
          <template #default="{ row }">
            <el-tag size="small">{{ row.type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="current_debt" label="当前欠款" width="120">
          <template #default="{ row }">
            <span class="debt-amount">¥{{ formatMoney(row.current_debt) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="credit_limit" label="额度" width="100">
          <template #default="{ row }">¥{{ formatMoney(row.credit_limit) }}</template>
        </el-table-column>
        <el-table-column label="使用率" width="120">
          <template #default="{ row }">
            <el-progress :percentage="row.usage_rate" :color="getUsageColor(row.usage_rate)" size="small" />
          </template>
        </el-table-column>
        <el-table-column prop="debt_order_count" label="欠单数" width="80" />
        <el-table-column label="最后欠款" width="160">
          <template #default="{ row }">{{ formatDate(row.last_debt_date) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="success" size="small" link @click="openRepay(row)">还款</el-button>
            <el-button type="primary" size="small" link @click="openStatement(row)">对账</el-button>
            <el-button type="warning" size="small" link @click="viewDebts(row)">欠款明细</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 还款对话框 -->
    <el-dialog v-model="repayVisible" title="客户还款" width="450px">
      <el-form v-if="repayCustomer" label-width="100px">
        <el-form-item label="客户名称">
          <strong>{{ repayCustomer.name }}</strong>
        </el-form-item>
        <el-form-item label="当前欠款">
          <span class="debt-amount">¥{{ formatMoney(repayCustomer.current_debt) }}</span>
        </el-form-item>
        <el-form-item label="还款金额" required>
          <el-input-number v-model="repayAmount" :min="0.01" :max="repayCustomer.current_debt" :precision="2" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="repayRemark" type="textarea" :rows="2" placeholder="还款备注（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="repayVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmRepay">确认还款</el-button>
      </template>
    </el-dialog>

    <!-- 欠款明细 -->
    <el-dialog v-model="debtsVisible" title="客户欠款明细" width="700px">
      <template v-if="customerDebts">
        <el-descriptions :column="3" border>
          <el-descriptions-item label="客户">{{ customerDebts.customer.name }}</el-descriptions-item>
          <el-descriptions-item label="当前欠款" :span="2">
            <span class="debt-amount">¥{{ formatMoney(customerDebts.customer.current_debt) }}</span>
          </el-descriptions-item>
        </el-descriptions>
        <el-divider content-position="left">欠款订单</el-divider>
        <el-table :data="customerDebts.debt_orders" border size="small" max-height="350">
          <el-table-column prop="order_no" label="单号" width="180" />
          <el-table-column label="日期" width="160">
            <template #default="{ row }">{{ formatDate(row.date) }}</template>
          </el-table-column>
          <el-table-column prop="total_amount" label="订单金额" width="110">
            <template #default="{ row }">¥{{ row.total_amount }}</template>
          </el-table-column>
          <el-table-column prop="debt_amount" label="欠款金额" width="110">
            <template #default="{ row }"><span class="debt-amount">¥{{ row.debt_amount }}</span></template>
          </el-table-column>
        </el-table>
      </template>
    </el-dialog>

    <!-- 对账单 -->
    <el-dialog v-model="statementVisible" title="客户对账单" width="900px" top="3vh">
      <template v-if="statementData">
        <el-descriptions :column="4" border>
          <el-descriptions-item label="客户名称">{{ statementData.customer.name }}</el-descriptions-item>
          <el-descriptions-item label="客户类型">{{ statementData.customer.type }}</el-descriptions-item>
          <el-descriptions-item label="信用额度">¥{{ formatMoney(statementData.customer.credit_limit) }}</el-descriptions-item>
          <el-descriptions-item label="当前欠款">
            <span class="debt-amount">¥{{ formatMoney(statementData.customer.current_debt) }}</span>
          </el-descriptions-item>
        </el-descriptions>

        <el-row :gutter="16" style="margin-top: 12px;">
          <el-col :span="6">
            <div class="mini-stat">订单数：{{ statementData.summary.order_count }}笔</div>
          </el-col>
          <el-col :span="6">
            <div class="mini-stat">总金额：<strong>¥{{ formatMoney(statementData.summary.total_amount) }}</strong></div>
          </el-col>
          <el-col :span="6">
            <div class="mini-stat">已收：<strong style="color: #67C23A;">¥{{ formatMoney(statementData.summary.total_paid) }}</strong></div>
          </el-col>
          <el-col :span="6">
            <div class="mini-stat">未收：<strong class="debt-amount">¥{{ formatMoney(statementData.summary.total_debt) }}</strong></div>
          </el-col>
        </el-row>

        <el-divider content-position="left">订单明细</el-divider>
        <el-table :data="statementData.orders" border size="small" max-height="400">
          <el-table-column prop="order_no" label="单号" width="180" />
          <el-table-column label="日期" width="160">
            <template #default="{ row }">{{ formatDate(row.date) }}</template>
          </el-table-column>
          <el-table-column label="商品数" width="80">
            <template #default="{ row }">{{ row.items.length }}</template>
          </el-table-column>
          <el-table-column prop="total_amount" label="金额" width="100">
            <template #default="{ row }">¥{{ row.total_amount }}</template>
          </el-table-column>
          <el-table-column prop="paid_amount" label="已收" width="100">
            <template #default="{ row }">
              <span style="color: #67C23A;">¥{{ row.paid_amount }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="debt_amount" label="欠款" width="100">
            <template #default="{ row }">
              <span :class="row.debt_amount > 0 ? 'debt-amount' : ''">¥{{ row.debt_amount }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="payment_type" label="结算方式" width="90" />
        </el-table>
      </template>
      <template #footer>
        <el-button @click="statementVisible = false">关闭</el-button>
        <el-button type="primary" @click="printStatement">打印对账单</el-button>
        <el-button type="success" @click="exportStatement">导出JSON</el-button>
      </template>
    </el-dialog>

    <!-- 批量还款 -->
    <el-dialog v-model="batchVisible" title="批量还款" width="600px">
      <el-table :data="batchItems" border size="small">
        <el-table-column prop="name" label="客户" min-width="120" />
        <el-table-column prop="current_debt" label="欠款" width="120">
          <template #default="{ row }">¥{{ formatMoney(row.current_debt) }}</template>
        </el-table-column>
        <el-table-column label="还款金额" width="160">
          <template #default="{ row }">
            <el-input-number v-model="row.repay_amount" :min="0" :max="row.current_debt" :precision="2" size="small" style="width: 140px;" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="60">
          <template #default="{ $index }">
            <el-button type="danger" size="small" link @click="batchItems.splice($index, 1)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-button style="margin-top: 10px;" size="small" @click="addBatchItem">+ 添加客户</el-button>
      <template #footer>
        <el-button @click="batchVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmBatchRepay">确认批量还款</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getDebtCustomers, getCustomerDebts, getCustomerStatement, repayCustomerDebt, batchRepay } from '@/api'

const loading = ref(false)
const debtCustomers = ref([])
const overdueList = ref([])
const filterType = ref('')

const repayVisible = ref(false)
const repayCustomer = ref(null)
const repayAmount = ref(0)
const repayRemark = ref('')

const debtsVisible = ref(false)
const customerDebts = ref(null)

const statementVisible = ref(false)
const statementData = ref(null)

const batchVisible = ref(false)
const batchItems = ref([])

const totalDebt = computed(() => debtCustomers.value.reduce((s, c) => s + c.current_debt, 0))
const overdueCount = computed(() => overdueList.value.length)
const repaidToday = ref(0)

const formatMoney = (val) => {
  const num = Number(val) || 0
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const getUsageColor = (rate) => {
  if (rate > 90) return '#F56C6C'
  if (rate > 70) return '#E6A23C'
  return '#409EFF'
}

const loadData = async () => {
  loading.value = true
  try {
    const params = {}
    if (filterType.value) params.customer_type = filterType.value
    debtCustomers.value = await getDebtCustomers(params)
    overdueList.value = await getOverdueCustomers()
  } catch (e) { /* handled */ }
  finally {
    loading.value = false
  }
}

const openRepay = (row) => {
  repayCustomer.value = row
  repayAmount.value = 0
  repayRemark.value = ''
  repayVisible.value = true
}

const confirmRepay = async () => {
  if (repayAmount.value <= 0) {
    ElMessage.warning('还款金额必须大于0')
    return
  }
  try {
    await repayCustomerDebt(repayCustomer.value.customer_id, repayAmount.value, repayRemark.value)
    ElMessage.success('还款成功')
    repayVisible.value = false
    loadData()
  } catch (e) { /* handled */ }
}

const viewDebts = async (row) => {
  try {
    customerDebts.value = await getCustomerDebts(row.customer_id)
    debtsVisible.value = true
  } catch (e) { /* handled */ }
}

const openStatement = async (row) => {
  try {
    statementData.value = await getCustomerStatement(row.customer_id)
    statementVisible.value = true
  } catch (e) { /* handled */ }
}

const printStatement = () => {
  ElMessage.info('打印功能：请使用浏览器打印（Ctrl+P）')
  window.print()
}

const exportStatement = () => {
  const dataStr = JSON.stringify(statementData.value, null, 2)
  const blob = new Blob([dataStr], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `对账单_${statementData.value.customer.name}_${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
}

const openBatchRepay = () => {
  batchItems.value = debtCustomers.value.filter(c => c.current_debt > 0).map(c => ({
    ...c, repay_amount: 0
  }))
  batchVisible.value = true
}

const addBatchItem = () => {
  ElMessageBox.prompt('请输入客户ID', '添加客户', {
    inputValidator: (v) => !v && '请输入客户ID'
  }).then(async ({ value }) => {
    try {
      const customer = await getCustomerDebts(parseInt(value))
      if (!batchItems.value.find(b => b.customer_id === parseInt(value))) {
        batchItems.value.push({
          customer_id: customer.customer.id,
          name: customer.customer.name,
          current_debt: customer.customer.current_debt,
          repay_amount: 0
        })
      }
    } catch (e) { /* handled */ }
  }).catch(() => {})
}

const confirmBatchRepay = async () => {
  const items = batchItems.value
    .filter(i => i.repay_amount > 0)
    .map(i => ({ customer_id: i.customer_id, amount: i.repay_amount }))

  if (!items.length) {
    ElMessage.warning('请至少添加一条还款')
    return
  }

  try {
    await ElMessageBox.confirm(`确认还款 ${items.length} 笔，共¥${formatMoney(items.reduce((s, i) => s + i.amount, 0))}？`, '批量还款确认')
    await batchRepay({ items })
    ElMessage.success('批量还款成功')
    batchVisible.value = false
    loadData()
  } catch (e) { /* handled */ }
}

onMounted(loadData)
</script>

<style scoped>
.stat-row {
  margin-bottom: 16px;
}
.stat-card {
  border-radius: 8px;
  padding: 16px;
  color: #fff;
  text-align: center;
}
.stat-card .stat-value {
  font-size: 24px;
  font-weight: bold;
}
.stat-card .stat-label {
  font-size: 13px;
  opacity: 0.9;
  margin-top: 4px;
}
.stat-card.blue { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.stat-card.orange { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
.stat-card.red { background: linear-gradient(135deg, #f5576c 0%, #c0392b 100%); }
.stat-card.green { background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); }

.debt-amount {
  color: #F56C6C;
  font-weight: bold;
}
.mini-stat {
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 4px;
  font-size: 14px;
}
</style>
