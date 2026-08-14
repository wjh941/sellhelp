import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

api.interceptors.response.use(
  response => response.data,
  error => {
    const message = error.response?.data?.detail || error.message || '请求失败'
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

// ========== 商品管理 ==========
export const getCategories = () => api.get('/categories')
export const createCategory = (data) => api.post('/categories', data)
export const updateCategory = (id, data) => api.put(`/categories/${id}`, data)
export const deleteCategory = (id) => api.delete(`/categories/${id}`)

export const getProducts = (params) => api.get('/products', { params })
export const getProduct = (id) => api.get(`/products/${id}`)
export const createProduct = (data) => api.post('/products', data)
export const updateProduct = (id, data) => api.put(`/products/${id}`, data)
export const deleteProduct = (id) => api.delete(`/products/${id}`)

// ========== 供应商管理 ==========
export const getSuppliers = (params) => api.get('/suppliers', { params })
export const createSupplier = (data) => api.post('/suppliers', data)
export const updateSupplier = (id, data) => api.put(`/suppliers/${id}`, data)
export const deleteSupplier = (id) => api.delete(`/suppliers/${id}`)

// ========== 客户管理 ==========
export const getCustomers = (params) => api.get('/customers', { params })
export const getCustomer = (id) => api.get(`/customers/${id}`)
export const createCustomer = (data) => api.post('/customers', data)
export const updateCustomer = (id, data) => api.put(`/customers/${id}`, data)
export const deleteCustomer = (id) => api.delete(`/customers/${id}`)
export const getCustomerSales = (id, params) => api.get(`/customers/${id}/sales`, { params })
export const payCustomerDebt = (id, amount) => api.post(`/customers/${id}/pay`, null, { params: { amount } })

// ========== 入库单 ==========
export const getPurchaseOrders = (params) => api.get('/purchase-orders', { params })
export const getPurchaseOrder = (id) => api.get(`/purchase-orders/${id}`)
export const createPurchaseOrder = (data) => api.post('/purchase-orders', data)
export const deletePurchaseOrder = (id) => api.delete(`/purchase-orders/${id}`)

// ========== 销售单 ==========
export const getSalesOrders = (params) => api.get('/sales-orders', { params })
export const getSalesOrder = (id) => api.get(`/sales-orders/${id}`)
export const createSalesOrder = (data) => api.post('/sales-orders', data)
export const updatePayment = (id, data) => api.post(`/sales-orders/${id}/pay`, data)
export const completePayment = (id) => api.post(`/sales-orders/${id}/complete-payment`)
export const deleteSalesOrder = (id) => api.delete(`/sales-orders/${id}`)

// ========== 库存管理 ==========
export const getStockSummary = () => api.get('/inventory/stock-summary')
export const getAllStock = (params) => api.get('/inventory/all-stock', { params })
export const getProductStock = (productId) => api.get(`/inventory/product/${productId}`)
export const getExpiryWarnings = (params) => api.get('/inventory/expiry-warnings', { params })
export const getLowStockAlerts = () => api.get('/inventory/low-stock')
export const getCategoriesStock = () => api.get('/inventory/categories-stock')

// ========== 退货管理 ==========
export const getReturns = (params) => api.get('/returns', { params })
export const createReturn = (data) => api.post('/returns', data)
export const getStockTakes = (params) => api.get('/stock-takes', { params })
export const prepareStockTake = (params) => api.post('/stock-takes/prepare', null, { params })
export const confirmStockTake = (data) => api.post('/stock-takes/confirm', data)

// ========== 行情与定价 ==========
export const getMarketPrices = (params) => api.get('/market-prices', { params })
export const createMarketPrice = (data) => api.post('/market-prices', data)
export const updateMarketPrice = (id, data) => api.put(`/market-prices/${id}`, data)
export const deleteMarketPrice = (id) => api.delete(`/market-prices/${id}`)

export const calculatePricing = (productId) => api.post('/pricing/calculate', { product_id: productId })
export const getPricingHistory = (params) => api.get('/pricing/history', { params })
export const confirmPricing = (referenceId, operator) => api.post(`/pricing/${referenceId}/confirm`, null, { params: { operator } })

// ========== 周报 ==========
export const getDashboardMetrics = () => api.get('/dashboard/metrics')
export const generateReport = (params) => api.post('/reports/generate', null, { params })
export const getLatestReport = () => api.get('/reports/latest')
export const getReports = (params) => api.get('/reports', { params })
export const getReport = (id) => api.get(`/reports/${id}`)

// ========== AI顾问 ==========
export const aiAsk = (data) => api.post('/ai-chat/ask', data)
export const getAISessions = () => api.get('/ai-chat/sessions')
export const getAISession = (sessionId) => api.get(`/ai-chat/sessions/${sessionId}`)
export const deleteAISession = (sessionId) => api.delete(`/ai-chat/sessions/${sessionId}`)

// ========== 导出打印 ==========
export const exportSalesOrder = (id, format = 'json') => api.get(`/export/sales/${id}`, { params: { format } })
export const exportPurchaseOrder = (id, format = 'json') => api.get(`/export/purchase/${id}`, { params: { format } })
export const exportCustomerStatement = (id, params) => api.get(`/export/customer-statement/${id}`, { params })
export const exportStockReport = (params) => api.get('/export/stock-report', { params })
export const exportExpiryReport = (params) => api.get('/export/expiry-report', { params })

// ========== 财务管理 ==========
export const getDebtCustomers = (params) => api.get('/finance/debt-customers', { params })
export const getCustomerDebts = (id) => api.get(`/finance/customer/${id}/debts`)
export const getCustomerStatement = (id, params) => api.get(`/finance/customer/${id}/statement`, { params })
export const repayCustomerDebt = (id, amount, remark) => api.post(`/finance/customer/${id}/repay`, null, { params: { amount, remark } })
export const getOverdueCustomers = () => api.get('/finance/overdue-customers')
export const batchRepay = (data) => api.post('/finance/batch-repay', data)

// ========== 系统管理 ==========
export const backupDatabase = () => api.post('/system/backup')
export const getBackups = () => api.get('/system/backups')
export const restoreDatabase = (filename) => api.post('/system/restore', null, { params: { backup_file: filename } })
export const deleteBackup = (filename) => api.delete(`/system/backups/${filename}`)
export const getSystemConfig = () => api.get('/system/config')
export const updateSystemConfig = (key, value, description) => api.put(`/system/config/${key}`, null, { params: { value, description } })
export const getSystemInfo = () => api.get('/system/info')
export const getSlowProducts = (params) => api.get('/system/slow-products', { params })
export const getClearSuggestion = (productId) => api.get(`/system/slow-products/${productId}/clear-suggestion`)
export const getOverstockAnalysis = () => api.get('/system/overstock-analysis')

// ========== 健康检查 ==========
export const healthCheck = () => api.get('/health')
