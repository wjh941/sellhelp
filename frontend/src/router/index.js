import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { title: '经营看板', icon: 'Odometer' }
  },
  {
    path: '/products',
    name: 'Products',
    component: () => import('@/views/Products.vue'),
    meta: { title: '商品管理', icon: 'Goods' }
  },
  {
    path: '/suppliers',
    name: 'Suppliers',
    component: () => import('@/views/Suppliers.vue'),
    meta: { title: '供应商管理', icon: 'OfficeBuilding' }
  },
  {
    path: '/customers',
    name: 'Customers',
    component: () => import('@/views/Customers.vue'),
    meta: { title: '客户管理', icon: 'User' }
  },
  {
    path: '/purchase',
    name: 'Purchase',
    component: () => import('@/views/Purchase.vue'),
    meta: { title: '入库开单', icon: 'Download' }
  },
  {
    path: '/sales',
    name: 'Sales',
    component: () => import('@/views/Sales.vue'),
    meta: { title: '销售开单', icon: 'Upload' }
  },
  {
    path: '/stock',
    name: 'Stock',
    component: () => import('@/views/Stock.vue'),
    meta: { title: '库存查询', icon: 'Histogram' }
  },
  {
    path: '/stock-analysis',
    name: 'StockAnalysis',
    component: () => import('@/views/StockAnalysis.vue'),
    meta: { title: '库存分析', icon: 'PieChart' }
  },
  {
    path: '/returns',
    name: 'Returns',
    component: () => import('@/views/Returns.vue'),
    meta: { title: '退货管理', icon: 'RefreshLeft' }
  },
  {
    path: '/finance',
    name: 'Finance',
    component: () => import('@/views/Finance.vue'),
    meta: { title: '回款管理', icon: 'Wallet' }
  },
  {
    path: '/market',
    name: 'Market',
    component: () => import('@/views/Market.vue'),
    meta: { title: '行情记录', icon: 'TrendCharts' }
  },
  {
    path: '/pricing',
    name: 'Pricing',
    component: () => import('@/views/Pricing.vue'),
    meta: { title: 'AI定价', icon: 'Money' }
  },
  {
    path: '/reports',
    name: 'Reports',
    component: () => import('@/views/Reports.vue'),
    meta: { title: '经营周报', icon: 'Document' }
  },
  {
    path: '/ai-chat',
    name: 'AIChat',
    component: () => import('@/views/AIChat.vue'),
    meta: { title: '生意顾问AI', icon: 'ChatDotRound' }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/Settings.vue'),
    meta: { title: '系统设置', icon: 'Setting' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
