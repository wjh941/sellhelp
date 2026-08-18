<template>
  <div>
    <el-tabs v-model="activeTab" type="border-card">
      <!-- 系统信息 -->
      <el-tab-pane label="ℹ️ 系统信息" name="info">
        <div class="page-card" v-loading="infoLoading">
          <div class="page-header">
            <h2>系统信息</h2>
            <el-button @click="loadInfo">刷新</el-button>
          </div>

          <el-row :gutter="16">
            <el-col :span="12">
              <el-descriptions :column="1" border v-if="systemInfo">
                <el-descriptions-item label="系统名称">{{ systemInfo.system }}</el-descriptions-item>
                <el-descriptions-item label="版本">{{ systemInfo.version }}</el-descriptions-item>
                <el-descriptions-item label="数据库路径">{{ systemInfo.database.path }}</el-descriptions-item>
                <el-descriptions-item label="数据库大小">{{ formatSize(systemInfo.database.size) }}</el-descriptions-item>
                <el-descriptions-item label="最近周报">
                  {{ systemInfo.latest_report || '暂无' }}
                </el-descriptions-item>
                <el-descriptions-item label="服务器时间">{{ formatDate(systemInfo.server_time) }}</el-descriptions-item>
              </el-descriptions>
            </el-col>
            <el-col :span="12">
              <h3>数据统计</h3>
              <el-descriptions :column="2" border v-if="systemInfo">
                <el-descriptions-item label="商品数">{{ systemInfo.database.tables.products }}</el-descriptions-item>
                <el-descriptions-item label="客户数">{{ systemInfo.database.tables.customers }}</el-descriptions-item>
                <el-descriptions-item label="供应商数">{{ systemInfo.database.tables.suppliers }}</el-descriptions-item>
                <el-descriptions-item label="销售单数">{{ systemInfo.database.tables.sales_orders }}</el-descriptions-item>
                <el-descriptions-item label="批次记录">{{ systemInfo.database.tables.batch_records }}</el-descriptions-item>
              </el-descriptions>
            </el-col>
          </el-row>
        </div>
      </el-tab-pane>

      <!-- 数据库备份 -->
      <el-tab-pane label="💾 数据库备份" name="backup">
        <div class="page-card">
          <div class="page-header">
            <h2>数据库备份管理</h2>
            <div class="actions">
              <el-button type="primary" @click="createBackup" :loading="backingUp">
                <el-icon><Download /></el-icon>立即备份
              </el-button>
              <el-button @click="loadBackups">刷新列表</el-button>
            </div>
          </div>

          <el-alert
            type="info"
            :closable="false"
            style="margin-bottom: 16px;"
            show-icon
          >
            <template #title>
              数据库存储所有经营数据，强烈建议定期备份。备份文件存放在数据库同级的 backup 目录。
            </template>
          </el-alert>

          <el-row :gutter="16" class="stat-row">
            <el-col :span="8">
              <div class="stat-card blue">
                <div class="stat-value">{{ backups.length }}</div>
                <div class="stat-label">备份文件数</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="stat-card orange">
                <div class="stat-value">{{ formatSize(totalBackupSize) }}</div>
                <div class="stat-label">备份总大小</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="stat-card green">
                <div class="stat-value">{{ lastBackupTime }}</div>
                <div class="stat-label">最近备份时间</div>
              </div>
            </el-col>
          </el-row>

          <el-table :data="backups" stripe v-loading="backupLoading">
            <el-table-column prop="filename" label="备份文件名" min-width="280">
              <template #default="{ row }">
                <el-icon><Document /></el-icon> {{ row.filename }}
              </template>
            </el-table-column>
            <el-table-column label="大小" width="120">
              <template #default="{ row }">{{ formatSize(row.size) }}</template>
            </el-table-column>
            <el-table-column label="创建时间" width="200">
              <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="200">
              <template #default="{ row }">
                <el-button type="primary" size="small" link @click="downloadBackup(row)">下载</el-button>
                <el-button type="warning" size="small" link @click="restoreBackup(row)">恢复</el-button>
                <el-button type="danger" size="small" link @click="handleDeleteBackup(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <!-- 使用说明 -->
      <el-tab-pane label="📖 使用说明" name="help">
        <div class="page-card">
          <div class="page-header">
            <h2>使用说明</h2>
          </div>

          <el-collapse>
            <el-collapse-item title="系统简介" name="1">
              <p>盈泰副食贸易管理系统是专为东莞高埗新联综合市场【盈泰副食贸易部】量身定制的完整商业经营管理系统。</p>
              <p>核心功能：</p>
              <ul>
                <li>📦 <strong>进销存管理</strong>：批次入库、FIFO先进先出、库存预警</li>
                <li>💰 <strong>三档价格体系</strong>：零售价、批发价、大客户价自动匹配</li>
                <li>📊 <strong>每周经营分析</strong>：热销/滞销分析、利润结构、库存风险</li>
                <li>🤖 <strong>AI生意顾问</strong>：副食行业赚钱逻辑库、经营问题AI问答</li>
                <li>📝 <strong>送货单打印</strong>：销售单、入库单一键打印</li>
              </ul>
            </el-collapse-item>

            <el-collapse-item title="快速上手" name="2">
              <p><strong>第一步：设置基础档案</strong></p>
              <p>进入"基础档案"模块，添加商品分类、商品信息、供应商、客户。</p>
              
              <p><strong>第二步：入库开单</strong></p>
              <p>进入"入库开单"模块，录入采购批次信息（批次号、生产日期、到期时间）。</p>
              
              <p><strong>第三步：销售开单</strong></p>
              <p>选择客户后系统自动匹配价格，自动按FIFO先进先出扣减库存。</p>
              
              <p><strong>第四步：查看周报</strong></p>
              <p>每周进入"经营周报"模块，一键生成本周经营分析报告。</p>
              
              <p><strong>第五步：AI咨询</strong></p>
              <p>遇到经营问题时，进入"生意顾问AI"模块，输入问题即可获得建议。</p>
            </el-collapse-item>

            <el-collapse-item title="特色功能说明" name="3">
              <p><strong>FIFO先进先出</strong>：系统自动按最早批次出库，防止商品过期造成损失。</p>
              <p><strong>AI不自动改价</strong>：AI定价仅供参考，最终价格由老板确认。</p>
              <p><strong>本地单机运行</strong>：所有数据存储在本地SQLite数据库，不上云、不泄露数据。</p>
              <p><strong>副食行业知识库</strong>：内置引流品逻辑、利润品逻辑、大客户锁客逻辑等10大商业套路。</p>
            </el-collapse-item>

            <el-collapse-item title="常见问题" name="4">
              <p><strong>Q: 忘记备份怎么办？</strong></p>
              <p>A: 立即进入"数据库备份"页面，点击"立即备份"创建备份。建议每周至少备份一次。</p>
              
              <p><strong>Q: 如何打印送货单？</strong></p>
              <p>A: 在销售单详情页，点击"打印"按钮使用浏览器打印功能。建议使用针式打印机。</p>
              
              <p><strong>Q: 如何查看某个客户的对账单？</strong></p>
              <p>A: 进入"客户管理"页面，点击客户详情中的"对账"按钮查看。</p>
              
              <p><strong>Q: 系统数据安全吗？</strong></p>
              <p>A: 数据存储在本地SQLite数据库文件中。建议定期备份并将备份文件复制到其他存储设备。</p>
            </el-collapse-item>
          </el-collapse>
        </div>
      </el-tab-pane>

      <el-tab-pane label="行情同步" name="market-sync">
        <div class="market-sync-panel" v-loading="marketSyncLoading">
          <div class="page-header">
            <h2>行情同步</h2>
            <el-tooltip content="刷新同步状态" placement="top">
              <el-button circle aria-label="刷新同步状态" @click="loadMarketSyncStatus">
                <el-icon><Refresh /></el-icon>
              </el-button>
            </el-tooltip>
          </div>

          <el-descriptions :column="1" border v-if="marketSyncStatus" class="market-sync-status">
            <el-descriptions-item label="服务端配置">
              <el-tag :type="marketSyncStatus.is_configured ? 'success' : 'warning'">
                {{ marketSyncStatus.is_configured ? '已配置' : '未配置' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="默认地区">{{ marketSyncStatus.default_region }}</el-descriptions-item>
            <el-descriptions-item label="最近运行">{{ formatMarketRun(marketSyncStatus.last_run) }}</el-descriptions-item>
          </el-descriptions>

          <el-form label-width="100px" class="market-sync-schedule" @submit.prevent="saveMarketSyncSchedule">
            <el-form-item label="每日同步时间">
              <el-input v-model="marketSyncTime" maxlength="5" placeholder="HH:MM" style="width: 140px;" />
              <el-button type="primary" :loading="savingMarketSync" @click="saveMarketSyncSchedule">保存</el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  getSystemInfo, backupDatabase, getBackups, 
  getExternalMarketSyncStatus, restoreDatabase, deleteBackup as deleteBackupApi,
  updateExternalMarketSyncSchedule
} from '@/api'
import { requestDesktopBackendRestart } from '@/utils/desktop'

const activeTab = ref('info')
const systemInfo = ref(null)
const infoLoading = ref(false)

const backups = ref([])
const backupLoading = ref(false)
const backingUp = ref(false)
const marketSyncStatus = ref(null)
const marketSyncLoading = ref(false)
const savingMarketSync = ref(false)
const marketSyncTime = ref('')

const formatSize = (bytes) => {
  if (!bytes) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(2) + ' MB'
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const totalBackupSize = computed(() => {
  return backups.value.reduce((s, b) => s + b.size, 0)
})

const lastBackupTime = computed(() => {
  if (!backups.value.length) return '无'
  return formatDate(backups.value[0].created_at)
})

const formatMarketRun = (run) => {
  if (!run) return '暂无运行记录'
  const time = formatDate(run.finished_at || run.started_at)
  const label = { success: '完成', partial: '部分完成', skipped: '已跳过' }[run.status] || '未完成'
  return `${time}（${label}）`
}

const loadMarketSyncStatus = async () => {
  marketSyncLoading.value = true
  try {
    marketSyncStatus.value = await getExternalMarketSyncStatus()
    marketSyncTime.value = marketSyncStatus.value.sync_time
  } catch (e) { /* Axios interceptor shows the backend error. */ }
  finally { marketSyncLoading.value = false }
}

const saveMarketSyncSchedule = async () => {
  if (!/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(marketSyncTime.value)) {
    ElMessage.warning('请输入严格的 HH:MM 24 小时时间。')
    return
  }
  savingMarketSync.value = true
  try {
    await updateExternalMarketSyncSchedule({ sync_time: marketSyncTime.value })
    ElMessage.success('行情同步时间已更新。')
    await loadMarketSyncStatus()
  } catch (e) { /* Axios interceptor shows the backend error. */ }
  finally { savingMarketSync.value = false }
}

const loadInfo = async () => {
  infoLoading.value = true
  try {
    systemInfo.value = await getSystemInfo()
  } catch (e) { /* handled */ }
  finally {
    infoLoading.value = false
  }
}

const loadBackups = async () => {
  backupLoading.value = true
  try {
    const result = await getBackups()
    backups.value = result.backups || []
  } catch (e) { /* handled */ }
  finally {
    backupLoading.value = false
  }
}

const createBackup = async () => {
  backingUp.value = true
  try {
    const result = await backupDatabase()
    ElMessage.success('备份成功')
    loadBackups()
  } catch (e) { /* handled */ }
  finally {
    backingUp.value = false
  }
}

const downloadBackup = (row) => {
  const baseUrl = '/api'
  const url = `${baseUrl}/system/backups/${encodeURIComponent(row.filename)}`
  window.open(url, '_blank')
}

const restoreBackup = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要将数据库恢复到备份"${row.filename}"？\n这将覆盖当前所有数据！`,
      '危险操作',
      { type: 'error' }
    )
    const result = await restoreDatabase(row.filename)
    const restarting = result.restart_required && await requestDesktopBackendRestart()
    ElMessage.success(restarting ? '恢复成功，正在重启系统' : '恢复成功，请重启系统')
  } catch (e) { /* handled */ }
}

const handleDeleteBackup = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除备份"${row.filename}"？`, '确认')
    await deleteBackupApi(row.filename)
    ElMessage.success('删除成功')
    loadBackups()
  } catch (e) { /* handled */ }
}

onMounted(() => {
  loadInfo()
  loadBackups()
  loadMarketSyncStatus()
})
</script>

<style scoped>
.stat-row { margin-bottom: 16px; }
.stat-card {
  border-radius: 8px;
  padding: 16px;
  color: #fff;
  text-align: center;
}
.stat-card .stat-value { font-size: 20px; font-weight: bold; }
.stat-card .stat-label { font-size: 13px; opacity: 0.9; margin-top: 4px; }
.stat-card.blue { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.stat-card.orange { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
.stat-card.green { background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); }
.market-sync-panel { padding: 4px; }
.market-sync-status { max-width: 560px; }
.market-sync-schedule { margin-top: 20px; }
.market-sync-schedule :deep(.el-form-item__content) { gap: 10px; }
</style>
