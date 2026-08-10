<template>
  <div>
    <div class="page-card">
      <div class="page-header">
        <h2>商品管理</h2>
        <div class="actions">
          <el-button type="primary" @click="openDialog()">
            <el-icon><Plus /></el-icon>
            新增商品
          </el-button>
        </div>
      </div>

      <div class="search-bar">
        <el-input v-model="searchKeyword" placeholder="搜索商品名称" style="width: 250px;" clearable @keyup.enter="loadData" />
        <el-select v-model="filterCategory" placeholder="商品分类" style="width: 150px;" clearable @change="loadData">
          <el-option v-for="cat in categories" :key="cat.id" :label="cat.name" :value="cat.id" />
        </el-select>
        <el-switch v-model="filterActive" active-text="在售" inactive-text="全部" @change="loadData" />
        <el-button type="primary" @click="loadData">
          <el-icon><Search /></el-icon>
          查询
        </el-button>
      </div>

      <el-table :data="products" stripe style="width: 100%" v-loading="loading">
        <el-table-column prop="code" label="编码" width="140" />
        <el-table-column prop="name" label="商品名称" min-width="180" />
        <el-table-column prop="category_name" label="分类" width="90">
          <template #default="{ row }">
            <el-tag size="small">{{ row.category_name || '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="spec" label="规格" width="100" />
        <el-table-column prop="unit" label="单位" width="70" />
        <el-table-column label="库存" width="80">
          <template #default="{ row }">
            <span :class="{ 'tag-danger': row.current_stock <= 0, 'tag-warning': row.current_stock > 0 && row.current_stock < row.safe_stock }">
              {{ row.current_stock }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="purchase_price" label="进价" width="80">
          <template #default="{ row }">¥{{ row.purchase_price }}</template>
        </el-table-column>
        <el-table-column prop="retail_price" label="零售" width="80">
          <template #default="{ row }">¥{{ row.retail_price }}</template>
        </el-table-column>
        <el-table-column prop="wholesale_price" label="批发" width="80">
          <template #default="{ row }">¥{{ row.wholesale_price }}</template>
        </el-table-column>
        <el-table-column prop="vip_price" label="VIP价" width="80">
          <template #default="{ row }">¥{{ row.vip_price }}</template>
        </el-table-column>
        <el-table-column prop="safe_stock" label="安全库存" width="80" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" link @click="openDialog(row)">编辑</el-button>
            <el-button type="warning" size="small" link @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @size-change="loadData"
        @current-change="loadData"
        style="margin-top: 20px; justify-content: flex-end;"
      />
    </div>

    <el-dialog v-model="dialogVisible" :title="editingProduct ? '编辑商品' : '新增商品'" width="700px">
      <el-form :model="form" label-width="100px" :rules="rules" ref="formRef">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="商品编码">
              <el-input v-model="form.code" placeholder="自动生成或自定义" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="商品名称" required>
              <el-input v-model="form.name" placeholder="请输入商品名称" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="商品分类">
              <el-select v-model="form.category_id" placeholder="选择分类" style="width: 100%;">
                <el-option v-for="cat in categories" :key="cat.id" :label="cat.name" :value="cat.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="规格">
              <el-input v-model="form.spec" placeholder="如：500ml、10kg" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="计量单位">
              <el-select v-model="form.unit" style="width: 100%;">
                <el-option label="件" value="件" />
                <el-option label="箱" value="箱" />
                <el-option label="袋" value="袋" />
                <el-option label="瓶" value="瓶" />
                <el-option label="桶" value="桶" />
                <el-option label="斤" value="斤" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="参考进价">
              <el-input-number v-model="form.purchase_price" :min="0" :precision="2" style="width: 100%;" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-divider content-position="left">三档价格体系</el-divider>
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="零售价">
              <el-input-number v-model="form.retail_price" :min="0" :precision="2" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="批发价">
              <el-input-number v-model="form.wholesale_price" :min="0" :precision="2" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="VIP价">
              <el-input-number v-model="form.vip_price" :min="0" :precision="2" style="width: 100%;" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-divider content-position="left">库存设置</el-divider>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="安全库存">
              <el-input-number v-model="form.safe_stock" :min="0" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="临期预警(天)">
              <el-input-number v-model="form.stock_alert_days" :min="7" :max="365" style="width: 100%;" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item>
          <el-switch v-model="form.is_active" active-text="在售" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- 分类管理 -->
    <div class="page-card" style="margin-top: 20px;">
      <div class="page-header">
        <h3>商品分类管理</h3>
      </div>
      <div style="display: flex; gap: 10px; flex-wrap: wrap;">
        <el-tag
          v-for="cat in categories"
          :key="cat.id"
          closable
          :type="getCategoryTagType(cat.id)"
          @close="handleDeleteCategory(cat.id)"
          style="font-size: 14px; padding: 8px 16px; cursor: pointer;"
          @click="editCategory(cat)"
        >
          {{ cat.name }}
        </el-tag>
        <el-button type="primary" size="small" @click="addCategory">+ 添加分类</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getCategories, getProducts, createProduct, updateProduct, deleteProduct,
  createCategory, deleteCategory
} from '@/api'

const loading = ref(false)
const products = ref([])
const categories = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const searchKeyword = ref('')
const filterCategory = ref(null)
const filterActive = ref(true)

const dialogVisible = ref(false)
const editingProduct = ref(null)
const formRef = ref(null)

const defaultForm = () => ({
  code: '',
  name: '',
  category_id: null,
  spec: '',
  unit: '件',
  purchase_price: 0,
  retail_price: 0,
  wholesale_price: 0,
  vip_price: 0,
  safe_stock: 0,
  stock_alert_days: 30,
  is_active: true,
  remark: ''
})

const form = reactive(defaultForm())

const rules = {
  name: [{ required: true, message: '请输入商品名称', trigger: 'blur' }]
}

const loadData = async () => {
  loading.value = true
  try {
    const params = {
      page: page.value,
      page_size: pageSize.value,
      keyword: searchKeyword.value || undefined,
      category_id: filterCategory.value || undefined,
      is_active: filterActive.value
    }
    const data = await getProducts(params)
    products.value = data.items || []
    total.value = data.total || 0
  } finally {
    loading.value = false
  }
}

const loadCategories = async () => {
  categories.value = await getCategories()
}

const openDialog = (product = null) => {
  editingProduct.value = product
  Object.assign(form, product || defaultForm())
  dialogVisible.value = true
}

const handleSave = async () => {
  if (!formRef.value) return
  await formRef.value.validate()

  try {
    if (editingProduct.value) {
      await updateProduct(editingProduct.value.id, form)
      ElMessage.success('更新成功')
    } else {
      await createProduct(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
  } catch (e) {
    // error handled by interceptor
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除商品"${row.name}"吗？`, '确认删除', { type: 'warning' })
    await deleteProduct(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch {
    // cancelled
  }
}

// 分类管理
const addCategory = async () => {
  const name = prompt('请输入分类名称：')
  if (name) {
    try {
      await createCategory({ name, sort_order: categories.value.length })
      loadCategories()
    } catch (e) { /* handled */ }
  }
}

const editCategory = (cat) => {
  const name = prompt('修改分类名称：', cat.name)
  if (name && name !== cat.name) {
    // 简单处理：这里应该有更新接口
    ElMessage.info('请使用分类标签上的删除按钮操作')
  }
}

const handleDeleteCategory = async (id) => {
  try {
    await ElMessageBox.confirm('确定删除此分类？', '确认', { type: 'warning' })
    await deleteCategory(id)
    loadCategories()
    loadData()
  } catch { /* cancelled */ }
}

const getCategoryTagType = (id) => {
  const types = ['', 'primary', 'success', 'warning', 'danger', 'info']
  return types[id % types.length]
}

onMounted(() => {
  loadCategories()
  loadData()
})
</script>
