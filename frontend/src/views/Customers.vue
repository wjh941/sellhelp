<template>
  <div>
    <div class="page-card">
      <div class="page-header">
        <h2>客户管理</h2>
        <div class="actions">
          <el-button type="primary" @click="openDialog()">
            <el-icon><Plus /></el-icon>新增客户
          </el-button>
        </div>
      </div>

      <div class="search-bar">
        <el-input v-model="keyword" placeholder="搜索客户名称" style="width: 220px;" clearable />
        <el-select v-model="filterType" placeholder="客户类型" style="width: 130px;" clearable>
          <el-option label="散户" value="散户" />
          <el-option label="小店" value="小店" />
          <el-option label="工厂" value="工厂" />
          <el-option label="食堂" value="食堂" />
          <el-option label="VIP" value="VIP" />
        </el-select>
        <el-switch v-model="filterDebt" active-text="有欠款" />
        <el-button type="primary" @click="loadData">
          <el-icon><Search /></el-icon>查询
        </el-button>
      </div>

      <el-table :data="customers" stripe v-loading="loading">
        <el-table-column prop="name" label="客户名称" min-width="150">
          <template #default="{ row }">
            {{ row.name }}
            <el-tag v-if="row.is_vip" type="danger" size="small" style="margin-left: 5px;">VIP</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="customer_type" label="类型" width="90" />
        <el-table-column prop="contact_person" label="联系人" width="100" />
        <el-table-column prop="phone" label="电话" width="120" />
        <el-table-column prop="credit_limit" label="额度" width="80">
          <template #default="{ row }">¥{{ row.credit_limit }}</template>
        </el-table-column>
        <el-table-column prop="current_debt" label="当前欠款" width="100">
          <template #default="{ row }">
            <span :class="row.current_debt > 0 ? 'tag-danger' : ''">¥{{ row.current_debt }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="total_consumption" label="累计消费" width="110">
          <template #default="{ row }">¥{{ row.total_consumption }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" link @click="openDialog(row)">编辑</el-button>
            <el-button v-if="row.current_debt > 0" type="success" size="small" link @click="handlePay(row)">还款</el-button>
            <el-button type="danger" size="small" link @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialogVisible" :title="editingCustomer ? '编辑客户' : '新增客户'" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="客户名称" required>
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="客户类型">
          <el-select v-model="form.customer_type" style="width: 100%;">
            <el-option label="散户" value="散户" />
            <el-option label="小店" value="小店" />
            <el-option label="工厂" value="工厂" />
            <el-option label="食堂" value="食堂" />
            <el-option label="VIP" value="VIP" />
          </el-select>
        </el-form-item>
        <el-form-item label="核心大客户">
          <el-switch v-model="form.is_vip" />
        </el-form-item>
        <el-form-item label="联系人">
          <el-input v-model="form.contact_person" />
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="form.phone" />
        </el-form-item>
        <el-form-item label="地址">
          <el-input v-model="form.address" type="textarea" />
        </el-form-item>
        <el-form-item label="欠款额度">
          <el-input-number v-model="form.credit_limit" :min="0" :precision="2" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="payDialogVisible" title="客户还款" width="400px">
      <el-form :model="payForm" label-width="80px">
        <el-form-item label="客户">
          <span>{{ payCustomer?.name }}</span>
        </el-form-item>
        <el-form-item label="欠款金额">
          <span class="tag-danger">¥{{ payCustomer?.current_debt }}</span>
        </el-form-item>
        <el-form-item label="还款金额">
          <el-input-number v-model="payForm.amount" :min="0" :max="payCustomer?.current_debt"
            :precision="2" style="width: 100%;" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="payDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmPay">确认还款</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getCustomers, createCustomer, updateCustomer, deleteCustomer, payCustomerDebt } from '@/api'

const loading = ref(false)
const customers = ref([])
const keyword = ref('')
const filterType = ref('')
const filterDebt = ref(false)

const dialogVisible = ref(false)
const payDialogVisible = ref(false)
const editingCustomer = ref(null)
const payCustomer = ref(null)

const defaultForm = () => ({
  name: '', customer_type: '散户', is_vip: false,
  contact_person: '', phone: '', address: '', credit_limit: 0, remark: ''
})

const form = reactive(defaultForm())
const payForm = reactive({ amount: 0 })

const loadData = async () => {
  loading.value = true
  try {
    customers.value = await getCustomers({
      keyword: keyword.value || undefined,
      customer_type: filterType.value || undefined,
      has_debt: filterDebt.value || undefined
    })
  } finally {
    loading.value = false
  }
}

const openDialog = (customer = null) => {
  editingCustomer.value = customer
  Object.assign(form, customer || defaultForm())
  dialogVisible.value = true
}

const handleSave = async () => {
  if (!form.name) {
    ElMessage.warning('请输入客户名称')
    return
  }
  try {
    if (editingCustomer.value) {
      await updateCustomer(editingCustomer.value.id, form)
      ElMessage.success('更新成功')
    } else {
      await createCustomer(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
  } catch (e) { /* handled */ }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除客户"${row.name}"？`, '确认', { type: 'warning' })
    await deleteCustomer(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch { /* cancelled */ }
}

const handlePay = (row) => {
  payCustomer.value = row
  payForm.amount = row.current_debt
  payDialogVisible.value = true
}

const confirmPay = async () => {
  try {
    await payCustomerDebt(payCustomer.value.id, payForm.amount)
    ElMessage.success('还款成功')
    payDialogVisible.value = false
    loadData()
  } catch (e) { /* handled */ }
}

onMounted(loadData)
</script>
