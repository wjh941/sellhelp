<template>
  <div class="archive-page">
    <section class="page-card supplier-workspace">
      <div class="page-header">
        <div><p class="section-kicker">基础档案</p><h2>供应商档案</h2><p class="section-description">集中维护采购联系人、账期和合作状态。</p></div>
        <el-button type="primary" @click="openDialog()"><el-icon><Plus /></el-icon>新增供应商</el-button>
      </div>
      <div class="filter-bar"><el-input v-model="keyword" placeholder="供应商名称、联系人或电话" clearable @keyup.enter="loadData"><template #prefix><el-icon><Search /></el-icon></template></el-input><el-button type="primary" @click="loadData">查询</el-button></div>
      <el-alert v-if="loadError" :title="loadError" type="error" :closable="false" show-icon class="archive-alert" />
      <div class="archive-table-scroll"><el-table :data="suppliers" stripe highlight-current-row class="data-table" v-loading="loading" empty-text="暂无符合条件的供应商"><el-table-column prop="name" label="供应商名称" min-width="190"><template #default="{ row }"><div class="supplier-name"><strong>{{ row.name }}</strong><small>{{ row.remark || '未填写备注' }}</small></div></template></el-table-column><el-table-column prop="contact_person" label="联系人" width="130"><template #default="{ row }">{{ row.contact_person || '-' }}</template></el-table-column><el-table-column prop="phone" label="联系电话" width="155"><template #default="{ row }">{{ row.phone || '-' }}</template></el-table-column><el-table-column prop="payment_term" label="账期说明" width="145"><template #default="{ row }">{{ row.payment_term || '-' }}</template></el-table-column><el-table-column label="合作状态" width="135"><template #default="{ row }"><el-tag :type="statusTagType(row.cooperation_status)" size="small">{{ row.cooperation_status || '未设置' }}</el-tag></template></el-table-column><el-table-column prop="address" label="地址" min-width="220" show-overflow-tooltip><template #default="{ row }">{{ row.address || '-' }}</template></el-table-column><el-table-column label="操作" fixed="right" width="175"><template #default="{ row }"><el-button link type="primary" @click="openDetail(row)">详情</el-button><el-button link type="primary" @click="openDialog(row)">编辑</el-button><el-button link type="danger" @click="handleDelete(row)">删除</el-button></template></el-table-column></el-table></div>
    </section>

    <el-dialog v-model="dialogVisible" :title="editingSupplier ? '编辑供应商档案' : '新增供应商档案'" width="min(620px, 94vw)" destroy-on-close><el-form :model="form" label-width="102px" class="grouped-form"><section class="form-section"><h3>联系信息</h3><el-form-item label="供应商名称" required><el-input v-model="form.name" placeholder="请输入供应商名称" /></el-form-item><el-row :gutter="18"><el-col :xs="24" :sm="12"><el-form-item label="联系人"><el-input v-model="form.contact_person" /></el-form-item></el-col><el-col :xs="24" :sm="12"><el-form-item label="联系电话"><el-input v-model="form.phone" /></el-form-item></el-col></el-row><el-form-item label="地址"><el-input v-model="form.address" type="textarea" :rows="2" /></el-form-item></section><section class="form-section"><h3>合作信息</h3><el-row :gutter="18"><el-col :xs="24" :sm="12"><el-form-item label="账期说明"><el-input v-model="form.payment_term" placeholder="如：月结30天" /></el-form-item></el-col><el-col :xs="24" :sm="12"><el-form-item label="合作状态"><el-select v-model="form.cooperation_status" style="width: 100%"><el-option v-for="status in cooperationStatuses" :key="status" :label="status" :value="status" /></el-select></el-form-item></el-col></el-row><el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="3" /></el-form-item></section></el-form><template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="handleSave">保存供应商</el-button></template></el-dialog>

    <el-dialog v-model="detailVisible" title="供应商档案详情" width="min(620px, 94vw)" destroy-on-close><div v-loading="detailLoading"><el-descriptions v-if="detailSupplier" :column="2" border class="supplier-detail"><el-descriptions-item label="供应商名称"><strong>{{ detailSupplier.name }}</strong></el-descriptions-item><el-descriptions-item label="合作状态"><el-tag :type="statusTagType(detailSupplier.cooperation_status)" size="small">{{ detailSupplier.cooperation_status || '未设置' }}</el-tag></el-descriptions-item><el-descriptions-item label="联系人">{{ detailSupplier.contact_person || '-' }}</el-descriptions-item><el-descriptions-item label="联系电话">{{ detailSupplier.phone || '-' }}</el-descriptions-item><el-descriptions-item label="账期说明" :span="2">{{ detailSupplier.payment_term || '-' }}</el-descriptions-item><el-descriptions-item label="地址" :span="2">{{ detailSupplier.address || '-' }}</el-descriptions-item><el-descriptions-item label="备注" :span="2">{{ detailSupplier.remark || '-' }}</el-descriptions-item></el-descriptions><el-empty v-else-if="!detailLoading" description="供应商详情不可用" /></div><template #footer><el-button @click="detailVisible = false">关闭</el-button><el-button v-if="detailSupplier" type="primary" @click="openDialog(detailSupplier); detailVisible = false">编辑供应商</el-button></template></el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createSupplier, deleteSupplier, getSuppliers, updateSupplier } from '@/api'

const cooperationStatuses = ['正常合作', '暂停合作', '待评估']
const loading = ref(false)
const saving = ref(false)
const loadError = ref('')
const suppliers = ref([])
const keyword = ref('')
const dialogVisible = ref(false)
const detailVisible = ref(false)
const detailLoading = ref(false)
const editingSupplier = ref(null)
const detailSupplier = ref(null)
const defaultForm = () => ({ name: '', contact_person: '', phone: '', address: '', payment_term: '', cooperation_status: '正常合作', remark: '' })
const form = reactive(defaultForm())
const supplierPayload = supplier => ({ name: supplier.name?.trim() || '', contact_person: supplier.contact_person || null, phone: supplier.phone || null, address: supplier.address || null, payment_term: supplier.payment_term || null, cooperation_status: supplier.cooperation_status || '正常合作', remark: supplier.remark || null })
const statusTagType = status => status === '正常合作' ? 'success' : status === '暂停合作' ? 'danger' : 'warning'
const loadData = async () => { loading.value = true; loadError.value = ''; try { suppliers.value = await getSuppliers({ keyword: keyword.value || undefined }) } catch { loadError.value = '供应商列表加载失败，请检查网络后重试。' } finally { loading.value = false } }
const openDialog = supplier => { editingSupplier.value = supplier || null; Object.assign(form, supplierPayload(supplier || defaultForm())); dialogVisible.value = true }
const handleSave = async () => { if (!form.name.trim()) return ElMessage.warning('请输入供应商名称'); saving.value = true; try { if (editingSupplier.value) { await updateSupplier(editingSupplier.value.id, supplierPayload(form)); ElMessage.success('供应商已更新') } else { await createSupplier(supplierPayload(form)); ElMessage.success('供应商已创建') } dialogVisible.value = false; loadData() } catch { /* response interceptor provides the backend message */ } finally { saving.value = false } }
const openDetail = row => { detailSupplier.value = row; detailVisible.value = true }
const handleDelete = async row => { try { await ElMessageBox.confirm(`确定删除供应商“${row.name}”吗？已有入库记录的供应商不能删除。`, '确认删除', { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' }); await deleteSupplier(row.id); ElMessage.success('供应商已删除'); loadData() } catch { /* cancelled or request failed */ } }
onMounted(loadData)
</script>

<style scoped>
.archive-page { display: grid; gap: 20px; }.supplier-workspace { margin-bottom: 0; }.section-kicker { color: var(--color-primary); font-size: 14px; font-weight: 600; margin-bottom: 5px; }.section-description { color: var(--color-muted); font-size: 14px; margin-top: 6px; }.filter-bar { align-items: center; display: flex; flex-wrap: wrap; gap: 10px; }.filter-bar :deep(.el-input) { width: min(340px, 100%); }.filter-bar :deep(.el-input__wrapper), .page-header :deep(.el-button) { min-height: 42px; }.archive-alert { margin-bottom: 14px; }.archive-table-scroll { overflow-x: auto; }.data-table { min-width: 1100px; }.supplier-name { display: grid; gap: 5px; }.supplier-name small { color: var(--color-muted); font-size: 14px; }.form-section { border-bottom: 1px solid var(--color-border); margin-bottom: 20px; padding-bottom: 4px; }.form-section:last-child { border-bottom: 0; margin-bottom: 0; }.form-section h3 { font-size: 16px; margin-bottom: 16px; }.supplier-detail :deep(.el-descriptions__label), .supplier-detail :deep(.el-descriptions__content) { font-size: 14px; }@media (max-width: 780px) { .page-header { align-items: flex-start; flex-direction: column; gap: 14px; }.filter-bar :deep(.el-input) { width: 100%; } }
</style>
