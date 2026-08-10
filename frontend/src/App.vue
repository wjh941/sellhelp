<template>
  <el-container class="app-container">
    <el-aside :width="isCollapsed ? '64px' : '220px'" class="app-aside">
      <div class="logo">
        <span v-if="!isCollapsed">盈泰副食</span>
        <span v-else>盈</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapsed"
        :collapse-transition="false"
        router
        background-color="#1e293b"
        text-color="#94a3b8"
        active-text-color="#409EFF"
      >
        <el-menu-item index="/">
          <el-icon><Odometer /></el-icon>
          <template #title>经营看板</template>
        </el-menu-item>

        <el-sub-menu index="archive">
          <template #title>
            <el-icon><Folder /></el-icon>
            <span>基础档案</span>
          </template>
          <el-menu-item index="/products">
            <el-icon><Goods /></el-icon>
            <template #title>商品管理</template>
          </el-menu-item>
          <el-menu-item index="/suppliers">
            <el-icon><OfficeBuilding /></el-icon>
            <template #title>供应商</template>
          </el-menu-item>
          <el-menu-item index="/customers">
            <el-icon><User /></el-icon>
            <template #title>客户管理</template>
          </el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="inventory">
          <template #title>
            <el-icon><Box /></el-icon>
            <span>进销存</span>
          </template>
          <el-menu-item index="/purchase">
            <el-icon><Download /></el-icon>
            <template #title>入库开单</template>
          </el-menu-item>
          <el-menu-item index="/sales">
            <el-icon><Upload /></el-icon>
            <template #title>销售开单</template>
          </el-menu-item>
          <el-menu-item index="/stock">
            <el-icon><Histogram /></el-icon>
            <template #title>库存查询</template>
          </el-menu-item>
          <el-menu-item index="/stock-analysis">
            <el-icon><PieChart /></el-icon>
            <template #title>库存分析</template>
          </el-menu-item>
          <el-menu-item index="/returns">
            <el-icon><RefreshLeft /></el-icon>
            <template #title>退货管理</template>
          </el-menu-item>
        </el-sub-menu>

        <el-menu-item index="/finance">
          <el-icon><Wallet /></el-icon>
          <template #title>回款管理</template>
        </el-menu-item>

        <el-sub-menu index="analysis">
          <template #title>
            <el-icon><DataAnalysis /></el-icon>
            <span>行情与分析</span>
          </template>
          <el-menu-item index="/market">
            <el-icon><TrendCharts /></el-icon>
            <template #title>行情记录</template>
          </el-menu-item>
          <el-menu-item index="/pricing">
            <el-icon><Money /></el-icon>
            <template #title>AI定价</template>
          </el-menu-item>
          <el-menu-item index="/reports">
            <el-icon><Document /></el-icon>
            <template #title>经营周报</template>
          </el-menu-item>
        </el-sub-menu>

        <el-menu-item index="/ai-chat">
          <el-icon><ChatDotRound /></el-icon>
          <template #title>生意顾问AI</template>
        </el-menu-item>

        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <template #title>系统设置</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="app-header">
        <div class="header-left">
          <el-icon class="collapse-btn" @click="isCollapsed = !isCollapsed">
            <Fold v-if="!isCollapsed" />
            <Expand v-else />
          </el-icon>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="currentRoute.meta?.title">
              {{ currentRoute.meta.title }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-tooltip content="数据库备份">
            <el-button circle @click="backupDB">
              <el-icon><Download /></el-icon>
            </el-button>
          </el-tooltip>
          <el-dropdown>
            <el-avatar :size="36" style="background: #409EFF;">盈</el-avatar>
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
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, Setting } from '@element-plus/icons-vue'
import { backupDatabase } from '@/api'

const route = useRoute()
const router = useRouter()
const isCollapsed = ref(false)

const activeMenu = computed(() => route.path)
const currentRoute = computed(() => route)

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
.app-container {
  height: 100vh;
}

.app-aside {
  background-color: #1e293b;
  transition: width 0.3s;
  overflow: hidden;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  font-weight: bold;
  background: linear-gradient(135deg, #409EFF, #67C23A);
  letter-spacing: 2px;
}

.app-header {
  background: #fff;
  border-bottom: 1px solid #e6e6e6;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;

  .header-left {
    display: flex;
    align-items: center;
    gap: 20px;

    .collapse-btn {
      font-size: 20px;
      cursor: pointer;
      color: #606266;

      &:hover {
        color: #409EFF;
      }
    }
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 15px;
  }
}

.app-main {
  background: #f5f7fa;
  padding: 20px;
  overflow-y: auto;
}

:deep(.el-menu) {
  border-right: none;
}
</style>
