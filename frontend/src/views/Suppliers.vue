<template>
  <div>
    <div class="page-card">
      <div class="page-header">
        <h2>供应商管理</h2>
        <div class="actions">
          <el-button type="primary" @click="openDialog()">
            <el-icon><Plus /></el-icon>新增供应商
          </el-button>
        </div>
      </div>

      <div class="search-bar">
        <el-input v-model="keyword" placeholder="搜索供应商名称" style="width: 250px;" clearable />
        <el-button type="primary" @click="loadData">
          <el-icon><Search /></el-icon>查询
        </el-button>
      </div>

      <el-table :data="suppliers" stripe v-loading="loading">
        <el-table-column prop="name" label="供应商名称" min-width="180" />
        <el-table-column prop="contact_person" label="联系人" width="100" />
        <el-table-column prop="phone" label="电话" width="130" />
        <el-table-column prop="address" label="地址" min-width="200" show-overflow-tooltip />
        <el-table-column prop="payment_term" label="账期" width="100" />
        <el-table-column prop="cooperation_status" label="合作状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.cooperation_status === '正常合作' ? 'success' : 'warning'" size="small">
              {{ row.cooperation_status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" link @click="openDialog(row)">编辑</el-button>
            <el-button type="danger" size="small" link @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialogVisible" :title="editingSupplier ? '编辑供应商' : '新增供应商'" width="500px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="供应商名称" required>
          <el-input v-model="form.name" />
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
        <el-form-item label="账期说明">
          <el-input v-model="form.payment_term" placeholder="如：月结30天" />
        </el-form-item>
        <el-form-item label="合作状态">
          <el-select v-model="form.cooperation_status" style="width: 100%;">
            <el-option label="正常合作" value="正常合作" />
            <el-option label="暂停合作" value="暂停合作" />
            <el-option label="待评估" value="待评估" />
          </el-select>
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
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getSuppliers, createSupplier, updateSupplier, deleteSupplier } from '@/api'

const loading = ref(false)
const suppliers = ref([])
const keyword = ref('')

const dialogVisible = ref(false)
const editingSupplier = ref(null)

const defaultForm = () => ({
  name: '', contact_person: '', phone: '', address: '',
  payment_term: '', cooperation_status: '正常合作', remark: ''
})

const form = reactive(defaultForm())

const loadData = async () => {
  loading.value = true
  try {
    suppliers.value = await getSuppliers({ keyword: keyword.value || undefined })
  } finally {
    loading.value = false
  }
}

const openDialog = (supplier = null) => {
  editingSupplier.value = supplier
  Object.assign(form, supplier || defaultForm())
  dialogVisible.value = true
}

const handleSave = async () => {
  try {
    if (editingSupplier.value) {
      await updateSupplier(editingSupplier.value.id, form)
      ElMessage.success('更新成功')
    } else {
      await createSupplier(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
  } catch (e) { /* handled */ }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除供应商"${row.name}"？`, '确认', { type: 'warning' })
    await deleteSupplier(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch { /* cancelled */ }
}

onMounted(loadData)
</script>
