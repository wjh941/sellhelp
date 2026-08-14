<template>
  <div>
    <div class="page-card">
      <div class="page-header">
        <h2>市场行情记录（人工录入）</h2>
        <div class="actions">
          <el-button type="primary" @click="openDialog()">
            <el-icon><Plus /></el-icon>录入行情
          </el-button>
        </div>
      </div>

      <el-alert type="info" :closable="false" style="margin-bottom: 20px;">
        <strong>合规说明：</strong>本系统不联网抓取数据，所有行情由老板人工录入，用于积累盈泰自己的私有行业数据库，越用越值钱。
      </el-alert>

      <div class="search-bar">
        <el-select v-model="filterType" placeholder="行情类型" style="width: 150px;" clearable>
          <el-option label="同行报价" value="同行报价" />
          <el-option label="厂家调价" value="厂家调价" />
          <el-option label="市场涨跌" value="市场涨跌" />
          <el-option label="节日行情" value="节日行情" />
          <el-option label="淡季行情" value="淡季行情" />
        </el-select>
        <el-date-picker v-model="filterDate" type="daterange" range-separator="至"
          start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" />
        <el-button type="primary" @click="loadData">查询</el-button>
      </div>

      <el-table :data="records" stripe v-loading="loading">
        <el-table-column prop="record_date" label="记录日期" width="110" />
        <el-table-column prop="price_type" label="行情类型" width="110">
          <template #default="{ row }">
            <el-tag size="small">{{ row.price_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="product_name" label="关联商品" min-width="150" />
        <el-table-column prop="competitor_price" label="同行报价" width="100">
          <template #default="{ row }">
            <span v-if="row.competitor_price">¥{{ row.competitor_price }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="manufacturer_price" label="厂家报价" width="100">
          <template #default="{ row }">
            <span v-if="row.manufacturer_price">¥{{ row.manufacturer_price }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="market_trend" label="市场趋势" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.market_trend" :type="getTrendType(row.market_trend)" size="small">
              {{ row.market_trend }}
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="content" label="行情详情" min-width="250" show-overflow-tooltip />
        <el-table-column prop="operator" label="录入人" width="100" />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button type="danger" size="small" link @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialogVisible" :title="editingRecord ? '编辑行情' : '录入行情'" width="600px">
      <el-form :model="form" label-width="100px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="记录日期" required>
              <el-date-picker v-model="form.record_date" type="date" placeholder="选择日期"
                value-format="YYYY-MM-DD" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="行情类型" required>
              <el-select v-model="form.price_type" style="width: 100%;">
                <el-option label="同行报价" value="同行报价" />
                <el-option label="厂家调价" value="厂家调价" />
                <el-option label="市场涨跌" value="市场涨跌" />
                <el-option label="节日行情" value="节日行情" />
                <el-option label="淡季行情" value="淡季行情" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="关联商品">
          <el-select v-model="form.product_id" placeholder="选择商品（可选）" filterable style="width: 100%;">
            <el-option v-for="p in products" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="同行报价">
              <el-input-number v-model="form.competitor_price" :min="0" :precision="2" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="厂家报价">
              <el-input-number v-model="form.manufacturer_price" :min="0" :precision="2" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="市场趋势">
              <el-select v-model="form.market_trend" style="width: 100%;" placeholder="趋势">
                <el-option label="上涨" value="上涨" />
                <el-option label="持平" value="持平" />
                <el-option label="下跌" value="下跌" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="行情详情">
          <el-input v-model="form.content" type="textarea" :rows="3" placeholder="详细描述行情情况..." />
        </el-form-item>
        <el-form-item label="操作员">
          <el-input v-model="form.operator" />
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
import {
  getMarketPrices, createMarketPrice, updateMarketPrice, deleteMarketPrice, getProducts
} from '@/api'

const loading = ref(false)
const records = ref([])
const products = ref([])
const filterType = ref('')
const filterDate = ref([])

const dialogVisible = ref(false)
const editingRecord = ref(null)

const today = new Date().toISOString().slice(0, 10)

const defaultForm = () => ({
  record_date: today, product_id: null, price_type: '同行报价',
  competitor_price: 0, manufacturer_price: 0, market_trend: '持平',
  content: '', remark: '', operator: ''
})

const form = reactive(defaultForm())

const getTrendType = (trend) => {
  if (trend === '上涨') return 'success'
  if (trend === '下跌') return 'danger'
  return 'info'
}

const loadData = async () => {
  loading.value = true
  try {
    const params = {}
    if (filterType.value) params.price_type = filterType.value
    if (filterDate.value?.length === 2) {
      params.start_date = filterDate.value[0]
      params.end_date = filterDate.value[1]
    }
    records.value = await getMarketPrices(params)
  } finally {
    loading.value = false
  }
}

const loadProducts = async () => {
  const data = await getProducts({ page_size: 100 })
  products.value = data.items || []
}

const openDialog = (record = null) => {
  editingRecord.value = record
  Object.assign(form, record || defaultForm())
  dialogVisible.value = true
}

const handleSave = async () => {
  try {
    if (editingRecord.value) {
      await updateMarketPrice(editingRecord.value.id, form)
      ElMessage.success('更新成功')
    } else {
      await createMarketPrice(form)
      ElMessage.success('录入成功')
    }
    dialogVisible.value = false
    loadData()
  } catch (e) { /* handled */ }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定删除此行情记录？', '确认', { type: 'warning' })
    await deleteMarketPrice(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch { /* cancelled */ }
}

onMounted(async () => {
  await loadProducts()
  loadData()
})
</script>
