import { createRouter, createWebHistory } from 'vue-router'
import { setUnauthorizedHandler } from '@/api'
import { canAccessRoute, clearAuthentication, initializeAuthentication, routeRoles } from '@/stores/auth'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { title: '经营看板', icon: 'Odometer', roles: routeRoles.Dashboard }
  },
  {
    path: '/products',
    name: 'Products',
    component: () => import('@/views/Products.vue'),
    meta: { title: '商品管理', icon: 'Goods', roles: routeRoles.Products }
  },
  {
    path: '/suppliers',
    name: 'Suppliers',
    component: () => import('@/views/Suppliers.vue'),
    meta: { title: '供应商管理', icon: 'OfficeBuilding', roles: routeRoles.Suppliers }
  },
  {
    path: '/customers',
    name: 'Customers',
    component: () => import('@/views/Customers.vue'),
    meta: { title: '客户管理', icon: 'User', roles: routeRoles.Customers }
  },
  {
    path: '/purchase',
    name: 'Purchase',
    component: () => import('@/views/Purchase.vue'),
    meta: { title: '入库开单', icon: 'Download', roles: routeRoles.Purchase }
  },
  {
    path: '/sales',
    name: 'Sales',
    component: () => import('@/views/Sales.vue'),
    meta: { title: '销售开单', icon: 'Upload', roles: routeRoles.Sales }
  },
  {
    path: '/stock',
    name: 'Stock',
    component: () => import('@/views/Stock.vue'),
    meta: { title: '库存查询', icon: 'Histogram', roles: routeRoles.Stock }
  },
  {
    path: '/stock-analysis',
    name: 'StockAnalysis',
    component: () => import('@/views/StockAnalysis.vue'),
    meta: { title: '库存分析', icon: 'PieChart', roles: routeRoles.StockAnalysis }
  },
  {
    path: '/stock-take-history',
    name: 'StockTakeHistory',
    component: () => import('@/views/StockTakeHistory.vue'),
    meta: { title: '库存盘点历史', icon: 'DocumentChecked', roles: routeRoles.StockTakeHistory }
  },
  {
    path: '/returns',
    name: 'Returns',
    component: () => import('@/views/Returns.vue'),
    meta: { title: '退货管理', icon: 'RefreshLeft', roles: routeRoles.Returns }
  },
  {
    path: '/finance',
    name: 'Finance',
    component: () => import('@/views/Finance.vue'),
    meta: { title: '回款管理', icon: 'Wallet', roles: routeRoles.Finance }
  },
  {
    path: '/customer-sales-history',
    name: 'CustomerSalesHistory',
    component: () => import('@/views/CustomerSalesHistory.vue'),
    meta: { title: '客户销售历史', icon: 'Tickets', roles: routeRoles.CustomerSalesHistory }
  },
  {
    path: '/market',
    name: 'Market',
    component: () => import('@/views/Market.vue'),
    meta: { title: '行情记录', icon: 'TrendCharts', roles: routeRoles.Market }
  },
  {
    path: '/pricing',
    name: 'Pricing',
    component: () => import('@/views/Pricing.vue'),
    meta: { title: 'AI定价', icon: 'Money', roles: routeRoles.Pricing }
  },
  {
    path: '/reports',
    name: 'Reports',
    component: () => import('@/views/Reports.vue'),
    meta: { title: '经营周报', icon: 'Document', roles: routeRoles.Reports }
  },
  {
    path: '/ai-chat',
    name: 'AIChat',
    component: () => import('@/views/AIChat.vue'),
    meta: { title: '生意顾问AI', icon: 'ChatDotRound', roles: routeRoles.AIChat }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/Settings.vue'),
    meta: { title: '系统设置', icon: 'Setting', roles: routeRoles.Settings }
  },
  {
    path: '/system-config',
    name: 'SystemConfig',
    component: () => import('@/views/SystemConfig.vue'),
    meta: { title: '配置管理', icon: 'Setting', roles: routeRoles.SystemConfig }
  },
  {
    path: '/accounts',
    name: 'Accounts',
    component: () => import('@/views/Accounts.vue'),
    meta: { title: '账户管理', icon: 'UserFilled', roles: routeRoles.Accounts }
  },
  {
    path: '/audit-logs',
    name: 'AuditLogs',
    component: () => import('@/views/AuditLogs.vue'),
    meta: { title: '审计日志', icon: 'DocumentChecked', roles: routeRoles.AuditLogs }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { public: true, title: '登录' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to) => {
  await initializeAuthentication()

  if (to.meta.public) {
    return canAccessRoute('Dashboard') ? { name: 'Dashboard' } : true
  }
  if (!canAccessRoute('Dashboard')) {
    return { name: 'Login', query: { redirect: to.fullPath } }
  }
  if (to.name && !canAccessRoute(to.name)) return { name: 'Dashboard' }
  return true
})

setUnauthorizedHandler(() => {
  clearAuthentication()
  if (router.currentRoute.value.name !== 'Login') {
    router.replace({ name: 'Login', query: { redirect: router.currentRoute.value.fullPath } })
  }
})

export default router
