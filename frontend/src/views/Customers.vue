<template>
  <div class="archive-page">
    <section class="page-card customer-workspace">
      <div class="page-header">
        <div><p class="section-kicker">基础档案</p><h2>客户档案</h2><p class="section-description">核对客户资料、累计消费与当前应收欠款。</p></div>
        <el-button type="primary" @click="openDialog()"><el-icon><Plus /></el-icon>新增客户</el-button>
      </div>
      <div class="filter-bar">
        <el-input v-model="keyword" placeholder="客户名称、联系人或电话" clearable @keyup.enter="loadData"><template #prefix><el-icon><Search /></el-icon></template></el-input>
        <el-select v-model="filterType" placeholder="全部类型" clearable @change="loadData"><el-option v-for="type in customerTypes" :key="type" :label="type" :value="type" /></el-select>
        <el-switch v-model="filterDebt" active-text="只看有欠款" inactive-text="全部客户" @change="loadData" />
        <el-button type="primary" @click="loadData">查询</el-button>
      </div>
      <el-alert v-if="loadError" :title="loadError" type="error" :closable="false" show-icon class="archive-alert" />
      <div class="archive-table-scroll">
        <el-table :data="customers" stripe highlight-current-row class="data-table" v-loading="loading" empty-text="暂无符合条件的客户">
          <el-table-column prop="name" label="客户名称" min-width="175">
            <template #default="{ row }"><div class="customer-name"><strong>{{ row.name }}</strong><div><el-tag v-if="isNamedVip(row)" type="warning" size="small">VIP · 晨升膳食</el-tag><el-tag v-else-if="row.is_vip" type="warning" size="small">VIP客户</el-tag><el-tag v-else size="small" effect="plain">{{ row.customer_type || '未分类' }}</el-tag></div></div></template>
          </el-table-column>
          <el-table-column prop="contact_person" label="联系人" width="120"><template #default="{ row }">{{ row.contact_person || '-' }}</template></el-table-column>
          <el-table-column prop="phone" label="联系电话" width="145"><template #default="{ row }">{{ row.phone || '-' }}</template></el-table-column>
          <el-table-column label="累计消费" width="130"><template #default="{ row }"><strong>{{ money(row.total_consumption) }}</strong></template></el-table-column>
          <el-table-column label="当前欠款" min-width="190"><template #default="{ row }"><div class="debt-cell"><strong :class="debtClass(row)">{{ money(row.current_debt) }}</strong><el-tag :type="debtTagType(row)" size="small">{{ debtStatus(row) }}</el-tag></div></template></el-table-column>
          <el-table-column label="欠款额度" width="130"><template #default="{ row }">{{ money(row.credit_limit) }}</template></el-table-column>
          <el-table-column prop="address" label="送货地址" min-width="180" show-overflow-tooltip><template #default="{ row }">{{ row.address || '-' }}</template></el-table-column>
          <el-table-column label="操作" fixed="right" width="220"><template #default="{ row }"><el-button link type="primary" @click="openDetail(row)">详情</el-button><el-button link type="primary" @click="openDialog(row)">编辑</el-button><el-button v-if="Number(row.current_debt) > 0" link type="success" @click="handlePay(row)">还款</el-button><el-button link type="danger" @click="handleDelete(row)">删除</el-button></template></el-table-column>
        </el-table>
      </div>
    </section>

    <el-dialog v-model="dialogVisible" :title="editingCustomer ? '编辑客户档案' : '新增客户档案'" width="min(620px, 94vw)" destroy-on-close>
      <el-form :model="form" label-width="102px" class="grouped-form"><section class="form-section"><h3>客户基础信息</h3><el-form-item label="客户名称" required><el-input v-model="form.name" placeholder="请输入客户名称" /></el-form-item><el-row :gutter="18"><el-col :xs="24" :sm="12"><el-form-item label="客户类型"><el-select v-model="form.customer_type" style="width: 100%"><el-option v-for="type in customerTypes" :key="type" :label="type" :value="type" /></el-select></el-form-item></el-col><el-col :xs="24" :sm="12"><el-form-item label="核心大客户"><el-switch v-model="form.is_vip" active-text="VIP" inactive-text="普通" /></el-form-item></el-col><el-col :xs="24" :sm="12"><el-form-item label="联系人"><el-input v-model="form.contact_person" /></el-form-item></el-col><el-col :xs="24" :sm="12"><el-form-item label="联系电话"><el-input v-model="form.phone" /></el-form-item></el-col></el-row><el-form-item label="送货地址"><el-input v-model="form.address" type="textarea" :rows="2" /></el-form-item></section><section class="form-section"><h3>授信与备注</h3><el-form-item label="欠款额度"><el-input-number v-model="form.credit_limit" :min="0" :precision="2" style="width: 100%" /></el-form-item><el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="3" /></el-form-item></section></el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="handleSave">保存客户</el-button></template>
    </el-dialog>

    <el-dialog v-model="detailVisible" title="客户档案详情" width="min(620px, 94vw)" destroy-on-close><div v-loading="detailLoading"><el-descriptions v-if="detailCustomer" :column="2" border class="customer-detail"><el-descriptions-item label="客户名称"><strong>{{ detailCustomer.name }}</strong><el-tag v-if="isNamedVip(detailCustomer)" type="warning" size="small" class="inline-tag">VIP · 晨升膳食</el-tag></el-descriptions-item><el-descriptions-item label="客户类型">{{ detailCustomer.customer_type || '-' }}</el-descriptions-item><el-descriptions-item label="联系人">{{ detailCustomer.contact_person || '-' }}</el-descriptions-item><el-descriptions-item label="联系电话">{{ detailCustomer.phone || '-' }}</el-descriptions-item><el-descriptions-item label="累计消费">{{ money(detailCustomer.total_consumption) }}</el-descriptions-item><el-descriptions-item label="当前欠款"><strong :class="debtClass(detailCustomer)">{{ money(detailCustomer.current_debt) }}</strong> · {{ debtStatus(detailCustomer) }}</el-descriptions-item><el-descriptions-item label="欠款额度">{{ money(detailCustomer.credit_limit) }}</el-descriptions-item><el-descriptions-item label="送货地址" :span="2">{{ detailCustomer.address || '-' }}</el-descriptions-item><el-descriptions-item label="备注" :span="2">{{ detailCustomer.remark || '-' }}</el-descriptions-item></el-descriptions><el-empty v-else-if="!detailLoading" description="客户详情不可用" /></div><template #footer><el-button @click="detailVisible = false">关闭</el-button><el-button v-if="detailCustomer" type="primary" @click="openDialog(detailCustomer); detailVisible = false">编辑客户</el-button></template></el-dialog>

    <el-dialog v-model="payDialogVisible" title="客户还款" width="min(430px, 94vw)" destroy-on-close><el-form :model="payForm" label-width="92px"><el-form-item label="客户"><strong>{{ payCustomer?.name }}</strong></el-form-item><el-form-item label="当前欠款"><strong class="danger-text">{{ money(payCustomer?.current_debt) }}</strong></el-form-item><el-form-item label="还款金额"><el-input-number v-model="payForm.amount" :min="0" :max="Number(payCustomer?.current_debt || 0)" :precision="2" style="width: 100%" /></el-form-item></el-form><template #footer><el-button @click="payDialogVisible = false">取消</el-button><el-button type="primary" :loading="paying" @click="confirmPay">确认还款</el-button></template></el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createCustomer, deleteCustomer, getCustomer, getCustomers, payCustomerDebt, updateCustomer } from '@/api'

const customerTypes = ['散户', '小店', '工厂', '食堂', 'VIP']
const loading = ref(false)
const saving = ref(false)
const paying = ref(false)
const loadError = ref('')
const customers = ref([])
const keyword = ref('')
const filterType = ref('')
const filterDebt = ref(false)
const dialogVisible = ref(false)
const detailVisible = ref(false)
const detailLoading = ref(false)
const payDialogVisible = ref(false)
const editingCustomer = ref(null)
const detailCustomer = ref(null)
const payCustomer = ref(null)
const defaultForm = () => ({ name: '', customer_type: '散户', is_vip: false, contact_person: '', phone: '', address: '', credit_limit: 0, remark: '' })
const form = reactive(defaultForm())
const payForm = reactive({ amount: 0 })
const number = value => Number(value || 0)
const money = value => `¥${number(value).toFixed(2)}`
const isNamedVip = row => row?.name === '晨升膳食'
const debtStatus = row => { const debt = number(row?.current_debt); const limit = number(row?.credit_limit); if (debt <= 0) return '无欠款'; if (limit > 0 && debt >= limit) return '额度已用满'; if (limit > 0 && debt / limit >= 0.8) return '接近额度'; return '有待收款' }
const debtTagType = row => { const status = debtStatus(row); return status === '无欠款' ? 'success' : status === '有待收款' ? 'warning' : 'danger' }
const debtClass = row => debtStatus(row) === '无欠款' ? 'success-text' : debtStatus(row) === '有待收款' ? 'warning-text' : 'danger-text'
const customerPayload = customer => ({ name: customer.name?.trim() || '', customer_type: customer.customer_type || '散户', is_vip: Boolean(customer.is_vip), contact_person: customer.contact_person || null, phone: customer.phone || null, address: customer.address || null, credit_limit: number(customer.credit_limit), remark: customer.remark || null })

const loadData = async () => { loading.value = true; loadError.value = ''; try { customers.value = await getCustomers({ keyword: keyword.value || undefined, customer_type: filterType.value || undefined, has_debt: filterDebt.value || undefined }) } catch { loadError.value = '客户列表加载失败，请检查网络后重试。' } finally { loading.value = false } }
const openDialog = customer => { editingCustomer.value = customer || null; Object.assign(form, customerPayload(customer || defaultForm())); dialogVisible.value = true }
const handleSave = async () => { if (!form.name.trim()) return ElMessage.warning('请输入客户名称'); saving.value = true; try { if (editingCustomer.value) { await updateCustomer(editingCustomer.value.id, customerPayload(form)); ElMessage.success('客户已更新') } else { await createCustomer(customerPayload(form)); ElMessage.success('客户已创建') } dialogVisible.value = false; loadData() } catch { /* response interceptor provides the backend message */ } finally { saving.value = false } }
const openDetail = async row => { detailVisible.value = true; detailLoading.value = true; detailCustomer.value = null; try { detailCustomer.value = await getCustomer(row.id) } catch { detailVisible.value = false } finally { detailLoading.value = false } }
const handleDelete = async row => { try { await ElMessageBox.confirm(`确定删除客户“${row.name}”吗？存在销售记录或欠款时不能删除。`, '确认删除', { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' }); await deleteCustomer(row.id); ElMessage.success('客户已删除'); loadData() } catch { /* cancelled or request failed */ } }
const handlePay = row => { payCustomer.value = row; payForm.amount = number(row.current_debt); payDialogVisible.value = true }
const confirmPay = async () => { if (number(payForm.amount) <= 0) return ElMessage.warning('还款金额必须大于 0'); paying.value = true; try { await payCustomerDebt(payCustomer.value.id, payForm.amount); ElMessage.success('还款已登记'); payDialogVisible.value = false; loadData() } catch { /* response interceptor provides the backend message */ } finally { paying.value = false } }

onMounted(loadData)
</script>

<style scoped>
.archive-page { display: grid; gap: 20px; }.customer-workspace { margin-bottom: 0; }.section-kicker { color: var(--color-primary); font-size: 14px; font-weight: 600; margin-bottom: 5px; }.section-description { color: var(--color-muted); font-size: 14px; margin-top: 6px; }.filter-bar { align-items: center; display: flex; flex-wrap: wrap; gap: 10px; }.filter-bar :deep(.el-input) { width: min(320px, 100%); }.filter-bar :deep(.el-select) { width: 180px; }.filter-bar :deep(.el-input__wrapper), .filter-bar :deep(.el-select__wrapper), .page-header :deep(.el-button) { min-height: 42px; }.archive-alert { margin-bottom: 14px; }.archive-table-scroll { overflow-x: auto; }.data-table { min-width: 1170px; }.customer-name, .debt-cell { display: grid; gap: 6px; }.debt-cell { align-items: center; grid-template-columns: auto max-content; }.danger-text { color: var(--color-danger); }.warning-text { color: var(--color-warning); }.success-text { color: var(--color-success); }.form-section { border-bottom: 1px solid var(--color-border); margin-bottom: 20px; padding-bottom: 4px; }.form-section:last-child { border-bottom: 0; margin-bottom: 0; }.form-section h3 { font-size: 16px; margin-bottom: 16px; }.inline-tag { margin-left: 8px; }.customer-detail :deep(.el-descriptions__label) { font-size: 14px; }.customer-detail :deep(.el-descriptions__content) { font-size: 14px; }@media (max-width: 780px) { .page-header { align-items: flex-start; flex-direction: column; gap: 14px; }.filter-bar :deep(.el-input), .filter-bar :deep(.el-select) { width: 100%; }.debt-cell { grid-template-columns: 1fr; } }
</style>
