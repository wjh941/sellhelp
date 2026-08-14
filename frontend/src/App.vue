<template>
  <el-container class="app-shell">
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
        <el-menu-item index="/">
          <el-icon><Odometer /></el-icon>
          <template #title>工作台</template>
        </el-menu-item>

        <el-sub-menu index="archive">
          <template #title>
            <el-icon><FolderOpened /></el-icon>
            <span>基础档案</span>
          </template>
          <el-menu-item index="/products"><el-icon><Goods /></el-icon><template #title>商品管理</template></el-menu-item>
          <el-menu-item index="/suppliers"><el-icon><OfficeBuilding /></el-icon><template #title>供应商管理</template></el-menu-item>
          <el-menu-item index="/customers"><el-icon><User /></el-icon><template #title>客户管理</template></el-menu-item>
        </el-sub-menu>

        <el-menu-item index="/purchase">
          <el-icon><Download /></el-icon>
          <template #title>入库业务</template>
        </el-menu-item>

        <el-sub-menu index="sales">
          <template #title>
            <el-icon><Tickets /></el-icon>
            <span>销售开单</span>
          </template>
          <el-menu-item index="/sales"><el-icon><Upload /></el-icon><template #title>销售开单</template></el-menu-item>
          <el-menu-item index="/finance"><el-icon><Wallet /></el-icon><template #title>回款管理</template></el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="stock">
          <template #title>
            <el-icon><Box /></el-icon>
            <span>退货盘点</span>
          </template>
          <el-menu-item index="/returns"><el-icon><RefreshLeft /></el-icon><template #title>退货管理</template></el-menu-item>
          <el-menu-item index="/stock"><el-icon><Histogram /></el-icon><template #title>库存查询</template></el-menu-item>
          <el-menu-item index="/stock-analysis"><el-icon><PieChart /></el-icon><template #title>库存分析</template></el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="market">
          <template #title>
            <el-icon><TrendCharts /></el-icon>
            <span>行情记录</span>
          </template>
          <el-menu-item index="/market"><el-icon><TrendCharts /></el-icon><template #title>行情记录</template></el-menu-item>
          <el-menu-item index="/pricing"><el-icon><Money /></el-icon><template #title>AI定价</template></el-menu-item>
        </el-sub-menu>

        <el-menu-item index="/reports">
          <el-icon><Document /></el-icon>
          <template #title>报表中心</template>
        </el-menu-item>
        <el-menu-item index="/ai-chat">
          <el-icon><ChatDotRound /></el-icon>
          <template #title>生意顾问</template>
        </el-menu-item>
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <template #title>系统设置</template>
        </el-menu-item>
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
          <el-tooltip content="数据库备份">
            <el-button class="header-icon-button" circle aria-label="备份数据库" @click="backupDB">
              <el-icon><Download /></el-icon>
            </el-button>
          </el-tooltip>
          <el-dropdown>
            <el-avatar :size="36" class="user-avatar">盈</el-avatar>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item>盈泰老板</el-dropdown-item>
                <el-dropdown-item divided>
                  <el-icon><Setting /></el-icon>
                  系统设置
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
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Box, ChatDotRound, Document, Download, Expand, Fold, FolderOpened, Goods, Histogram,
  Money, Moon, Odometer, OfficeBuilding, PieChart, RefreshLeft, Setting, Shop, Sunny,
  Tickets, TrendCharts, Upload, User, Wallet,
} from '@element-plus/icons-vue'
import { backupDatabase } from '@/api'
import { writeTheme } from '@/utils/operationUi'

const route = useRoute()
const isCollapsed = ref(false)
const theme = ref(document.documentElement.dataset.theme || 'light')
const clock = ref('')
let clockTimer

const activeMenu = computed(() => route.path)
const currentRoute = computed(() => route)
const isDark = computed(() => theme.value === 'dark')

const updateClock = () => {
  clock.value = new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
  }).format(new Date())
}

const toggleTheme = () => {
  theme.value = isDark.value ? 'light' : 'dark'
  document.documentElement.dataset.theme = theme.value
  writeTheme(theme.value, window.localStorage)
}

onMounted(() => {
  updateClock()
  clockTimer = window.setInterval(updateClock, 1000)
})

onBeforeUnmount(() => window.clearInterval(clockTimer))

const backupDB = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要备份数据库吗？建议每周至少备份一次！',
      '数据库备份',
      { type: 'warning' }
    )
    const result = await backupDatabase()
    ElMessage.success(`备份成功：${result.backup_file}`)
  } catch {
    // 用户取消或已处理
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
