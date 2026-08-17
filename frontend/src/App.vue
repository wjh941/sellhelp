<template>
  <el-config-provider :locale="zhCn">
    <router-view v-if="isLoginRoute" />

    <el-container v-else class="app-shell">
      <el-aside :width="isCollapsed ? '72px' : '248px'" class="app-aside">
        <div class="brand" :class="{ 'is-collapsed': isCollapsed }">
          <el-icon><Shop /></el-icon>
          <span v-if="!isCollapsed">盈泰副食</span>
        </div>

        <el-menu
          :default-active="activeMenu"
          :collapse="isCollapsed"
          :collapse-transition="false"
          router
          class="side-menu"
        >
          <el-menu-item v-if="canAccessRoute('Dashboard')" index="/">
            <el-icon><Odometer /></el-icon>
            <template #title>工作台</template>
          </el-menu-item>

          <el-sub-menu v-if="hasAnyAccess(['Products', 'Suppliers', 'Customers'])" index="archive">
            <template #title>
              <el-icon><FolderOpened /></el-icon>
              <span>基础档案</span>
            </template>
            <el-menu-item v-if="canAccessRoute('Products')" index="/products"><el-icon><Goods /></el-icon><template #title>商品管理</template></el-menu-item>
            <el-menu-item v-if="canAccessRoute('Suppliers')" index="/suppliers"><el-icon><OfficeBuilding /></el-icon><template #title>供应商管理</template></el-menu-item>
            <el-menu-item v-if="canAccessRoute('Customers')" index="/customers"><el-icon><User /></el-icon><template #title>客户管理</template></el-menu-item>
          </el-sub-menu>

          <el-menu-item v-if="canAccessRoute('Purchase')" index="/purchase">
            <el-icon><Download /></el-icon>
            <template #title>入库业务</template>
          </el-menu-item>

          <el-sub-menu v-if="hasAnyAccess(['Sales', 'Finance'])" index="sales">
            <template #title>
              <el-icon><Tickets /></el-icon>
              <span>销售开单</span>
            </template>
            <el-menu-item v-if="canAccessRoute('Sales')" index="/sales"><el-icon><Upload /></el-icon><template #title>销售开单</template></el-menu-item>
            <el-menu-item v-if="canAccessRoute('Finance')" index="/finance"><el-icon><Wallet /></el-icon><template #title>回款管理</template></el-menu-item>
          </el-sub-menu>

          <el-sub-menu v-if="hasAnyAccess(['Returns', 'Stock', 'StockAnalysis'])" index="stock">
            <template #title>
              <el-icon><Box /></el-icon>
              <span>退货盘点</span>
            </template>
            <el-menu-item v-if="canAccessRoute('Returns')" index="/returns"><el-icon><RefreshLeft /></el-icon><template #title>退货管理</template></el-menu-item>
            <el-menu-item v-if="canAccessRoute('Stock')" index="/stock"><el-icon><Histogram /></el-icon><template #title>库存查询</template></el-menu-item>
            <el-menu-item v-if="canAccessRoute('StockAnalysis')" index="/stock-analysis"><el-icon><PieChart /></el-icon><template #title>库存分析</template></el-menu-item>
          </el-sub-menu>

          <el-sub-menu v-if="hasAnyAccess(['Market', 'Pricing'])" index="market">
            <template #title>
              <el-icon><TrendCharts /></el-icon>
              <span>行情定价</span>
            </template>
            <el-menu-item v-if="canAccessRoute('Market')" index="/market"><el-icon><TrendCharts /></el-icon><template #title>行情记录</template></el-menu-item>
            <el-menu-item v-if="canAccessRoute('Pricing')" index="/pricing"><el-icon><Money /></el-icon><template #title>AI 定价</template></el-menu-item>
          </el-sub-menu>

          <el-menu-item v-if="canAccessRoute('Reports')" index="/reports">
            <el-icon><Document /></el-icon>
            <template #title>报表中心</template>
          </el-menu-item>
          <el-menu-item v-if="canAccessRoute('AIChat')" index="/ai-chat">
            <el-icon><ChatDotRound /></el-icon>
            <template #title>生意顾问</template>
          </el-menu-item>
          <el-sub-menu v-if="hasAnyAccess(['Settings', 'Accounts', 'AuditLogs'])" index="administration">
            <template #title>
              <el-icon><Setting /></el-icon>
              <span>系统管理</span>
            </template>
            <el-menu-item v-if="canAccessRoute('Settings')" index="/settings"><el-icon><Setting /></el-icon><template #title>系统设置</template></el-menu-item>
            <el-menu-item v-if="canAccessRoute('Accounts')" index="/accounts"><el-icon><UserFilled /></el-icon><template #title>账户管理</template></el-menu-item>
            <el-menu-item v-if="canAccessRoute('AuditLogs')" index="/audit-logs"><el-icon><DocumentChecked /></el-icon><template #title>审计日志</template></el-menu-item>
          </el-sub-menu>
        </el-menu>
      </el-aside>

      <el-container class="app-workspace">
        <el-header class="app-header">
          <div class="header-left">
            <el-tooltip :content="isCollapsed ? '展开导航' : '收起导航'">
              <el-button class="header-icon-button" circle aria-label="切换导航" @click="isCollapsed = !isCollapsed">
                <el-icon><Fold v-if="!isCollapsed" /><Expand v-else /></el-icon>
              </el-button>
            </el-tooltip>
            <el-breadcrumb separator="/">
              <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
              <el-breadcrumb-item v-if="currentRoute.meta?.title">{{ currentRoute.meta.title }}</el-breadcrumb-item>
            </el-breadcrumb>
          </div>

          <div class="header-right">
            <span class="header-clock" aria-label="当前时间">{{ clock }}</span>
            <el-button class="theme-toggle" :aria-label="`切换至${isDark ? '浅色' : '深色'}模式`" @click="toggleTheme">
              <el-icon><Moon v-if="!isDark" /><Sunny v-else /></el-icon>
              {{ isDark ? '深色模式' : '浅色模式' }}
            </el-button>
            <el-tooltip v-if="auth.hasRole('owner')" content="数据库备份">
              <el-button class="header-icon-button" circle aria-label="备份数据库" @click="backupDB">
                <el-icon><Download /></el-icon>
              </el-button>
            </el-tooltip>
            <el-dropdown @command="handleAccountCommand">
              <el-avatar :size="36" class="user-avatar">{{ userInitial }}</el-avatar>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item disabled>{{ auth.state.user?.display_name || '当前操作员' }}</el-dropdown-item>
                  <el-dropdown-item disabled>{{ roleLabel }}</el-dropdown-item>
                  <el-dropdown-item v-if="canAccessRoute('Accounts')" divided command="accounts">
                    <el-icon><UserFilled /></el-icon>
                    账户管理
                  </el-dropdown-item>
                  <el-dropdown-item v-if="!auth.state.standalone_mode" divided command="logout">
                    <el-icon><SwitchButton /></el-icon>
                    退出登录
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </el-header>

        <el-main class="app-main">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </el-config-provider>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import {
  Box, ChatDotRound, Document, DocumentChecked, Download, Expand, Fold, FolderOpened, Goods,
  Histogram, Money, Moon, Odometer, OfficeBuilding, PieChart, RefreshLeft, Setting, Shop,
  Sunny, SwitchButton, Tickets, TrendCharts, Upload, User, UserFilled, Wallet,
} from '@element-plus/icons-vue'
import { backupDatabase } from '@/api'
import { useAuth } from '@/stores/auth'
import { writeTheme } from '@/utils/operationUi'

const route = useRoute()
const router = useRouter()
const auth = useAuth()
const isCollapsed = ref(false)
const theme = ref(document.documentElement.dataset.theme || 'light')
const clock = ref('')
let clockTimer

const activeMenu = computed(() => route.path)
const currentRoute = computed(() => route)
const isDark = computed(() => theme.value === 'dark')
const isLoginRoute = computed(() => route.name === 'Login')
const userInitial = computed(() => (auth.state.user?.display_name || '员').slice(0, 1))
const roleLabel = computed(() => {
  const labels = { owner: '系统负责人', warehouse_operator: '仓库操作员', sales_clerk: '销售开单员' }
  return (auth.state.user?.role_codes || []).map(role => labels[role] || role).join(' / ')
})

const canAccessRoute = name => auth.canAccessRoute(name)
const hasAnyAccess = names => names.some(canAccessRoute)

const updateClock = () => {
  clock.value = new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
  }).format(new Date())
}

const toggleTheme = () => {
  theme.value = isDark.value ? 'light' : 'dark'
  document.documentElement.dataset.theme = theme.value
  writeTheme(theme.value, window.localStorage)
  document.dispatchEvent(new CustomEvent('yingtai-theme-change'))
}

onMounted(() => {
  updateClock()
  clockTimer = window.setInterval(updateClock, 1000)
})

onBeforeUnmount(() => window.clearInterval(clockTimer))

const backupDB = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要备份数据库吗？建议每周至少备份一次。',
      '数据库备份',
      { type: 'warning' }
    )
    const result = await backupDatabase()
    ElMessage.success(`备份成功：${result.backup_file}`)
  } catch {
    // The action was cancelled or the API showed its failure message.
  }
}

const handleAccountCommand = async command => {
  if (command === 'accounts') {
    router.push({ name: 'Accounts' })
    return
  }
  if (command === 'logout') {
    await auth.signOut()
    router.replace({ name: 'Login' })
  }
}
</script>

<style lang="scss" scoped>
.app-shell,
.app-workspace {
  height: 100vh;
  min-width: 0;
}

.app-aside {
  background: var(--shell-sidebar);
  border-right: 1px solid var(--shell-sidebar-border);
  overflow: hidden;
}

.brand {
  align-items: center;
  color: var(--shell-sidebar-text);
  display: flex;
  font-size: 18px;
  font-weight: 700;
  gap: 12px;
  height: 64px;
  padding: 0 22px;
  white-space: nowrap;

  .el-icon {
    color: var(--color-primary);
    font-size: 24px;
  }

  &.is-collapsed {
    justify-content: center;
    padding: 0;
  }
}

.side-menu {
  --el-menu-bg-color: transparent;
  --el-menu-text-color: var(--shell-sidebar-muted);
  --el-menu-active-color: var(--shell-sidebar-text);
  --el-menu-hover-bg-color: var(--shell-sidebar-hover);
  --el-menu-item-height: 46px;
  --el-menu-sub-item-height: 44px;
  border-right: 0;
}

.app-header {
  align-items: center;
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  height: 64px;
  justify-content: space-between;
  padding: 0 24px;
}

.header-left,
.header-right {
  align-items: center;
  display: flex;
  gap: 12px;
  min-width: 0;
}

.header-clock {
  color: var(--color-muted);
  font-size: 14px;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.header-icon-button {
  min-height: 40px;
  min-width: 40px;
}

.theme-toggle {
  min-height: 40px;
}

.user-avatar {
  background: var(--color-primary);
  color: #fff;
  cursor: pointer;
}

.app-main {
  background: var(--color-page);
  min-width: 0;
  overflow-y: auto;
  padding: 20px 24px;
}

:deep(.el-menu-item),
:deep(.el-sub-menu__title) {
  margin: 2px 8px;
  width: auto;
}

:deep(.el-menu-item.is-active) {
  background: var(--shell-sidebar-active);
  border-radius: 6px;
}

@media (max-width: 760px) {
  .app-header { padding: 0 12px; }
  .header-clock { display: none; }
  .theme-toggle { padding: 0 10px; }
  .app-main { padding: 14px; }
}
</style>
