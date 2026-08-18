# Sellhelp

## Windows Desktop Installer

Windows 10/11 x64 users can build an unsigned NSIS installer with
`powershell -ExecutionPolicy Bypass -File scripts\build-desktop.ps1`.
The result is `desktop\release\SellHelp Setup 1.0.0.exe`. The installed
application starts its bundled backend locally and does not require Python,
Node.js, or network access after installation. Because the installer is not
code-signed yet, Windows may show a publisher warning.

Uninstall keeps application data, backups, logs, and the desktop login secret
under `%LOCALAPPDATA%\SellHelp`.

盈泰副食贸易部经营管理系统。该项目使用 FastAPI、SQLite、Vue 3、Vite 和 Element Plus，为副食档口的入库、销售、库存风险、客户欠款和经营复盘提供本地化管理界面。

## 已完成的前端功能

- 经营工作台：今日/本周销售、应收欠款、库存资金、临期、低库存、逾期欠款与热销/滞销风险提示；风险项支持本地暂时忽略和快捷跳转。
- 销售开单：可拖动三栏开单区、客户价格档位、欠款额度提醒、订单实时合计、草稿恢复、F5 新建、Escape 清空、送货单预览和浏览器打印。
- 入库开单：可拖动批次录入、商品联想、批次/生产/到期日期、实时金额、草稿恢复、保质期提示和字段级校验。
- 基础档案：商品表格/卡片视图、三档价格和安全库存提示、受控备注/安全库存编辑；客户 VIP/欠款状态；供应商分组信息与 CRUD。
- 库存与退货盘点：批次库存风险、客户/供应商退货伙伴选择与数量上限、盘盈盘亏实时提示、库存分析。
- 行情、定价与报表：行情时间线和本地筛选、外部行情审核、定价模拟毛利预览、周报筛选/打印/CSV 导出。

所有上述界面保留既有后端接口和 SQLite 字段。主题、草稿、表格布局、局部筛选和模拟价格只保存在浏览器本地，不会修改服务端业务数据。

## 环境要求

- Python 3.11
- Node.js 18 或更高版本

## 全新克隆后的初始化

在仓库根目录安装后端和前端依赖：

```powershell
pip install -r backend/requirements.txt
npm ci --prefix frontend
```

在 Windows 上运行 `start.bat`，即可初始化本地数据库并启动前后端服务。前端访问地址为 http://localhost:8080，后端 API 文档地址为 http://localhost:8001/docs。

仅开发前端时：

```powershell
Set-Location frontend
npm.cmd run dev
```

Vite 开发服务器默认监听 http://localhost:8080，并将现有 API 请求代理到后端。

## 配置说明

`SELLHELP_DATABASE_URL` 可覆盖默认 SQLite 数据库连接，例如：

```powershell
$env:SELLHELP_DATABASE_URL = "sqlite:///C:/data/sellhelp.db"
```

`SELLHELP_ALLOWED_ORIGINS` 是 CORS 允许访问的浏览器来源列表，使用逗号分隔，默认值为 `http://localhost:8080`：

```powershell
$env:SELLHELP_ALLOWED_ORIGINS = "http://localhost:8080,http://example.local"
```

### 外部行情同步

只在后端服务环境中配置 `ANYSEARCH_API_KEY`，然后重启后端使配置生效。不要将该值放入浏览器、前端构建产物或版本控制系统。

```powershell
$env:ANYSEARCH_API_KEY = "your-server-side-key"
```

默认情况下，外部行情数据会在 `Asia/Shanghai` 时区每天 `02:00` 同步。可在系统设置中调整计划。网络报价始终处于待审核状态，只有操作员手动确认后，才会影响本地行情价格和定价计算。

同步使用国家发展和改革委员会公开价格监测信息、国家粮食和物资储备局公开信息以及公开零售搜索结果。外部内容可能存在延迟、不完整或促销属性，操作员接受报价前必须核验来源和零售场景。

## 验证

运行后端测试：

```powershell
Set-Location backend
python -m pytest -q
```

运行全部前端检查：

```powershell
Set-Location frontend
npm.cmd test
npm.cmd run build
```

仅构建前端：

```powershell
Set-Location frontend
npm.cmd run build
```

## 备份与恢复

应用创建的数据库备份保存在 `backend/backup` 目录中。执行数据库恢复前，系统也会在该目录创建恢复前备份。

对文件型 SQLite 数据库执行 Alembic 前，请停止后端并将数据库文件复制到安全位置。非破坏性迁移步骤请参阅 `backend/ALEMBIC.md`。
