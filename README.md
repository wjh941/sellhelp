# Sellhelp

盈泰副食贸易部经营管理系统。该项目使用 FastAPI、SQLite、Vue 3、Vite 和 Element Plus，为副食档口的入库、销售、库存风险、客户欠款和经营复盘提供本地化管理界面。

## 已完成的前端功能

- 经营工作台：今日/本周销售、应收欠款、库存资金、临期、低库存、逾期欠款与热销/滞销风险提示；风险项支持本地暂时忽略和快捷跳转。
- 销售开单：可拖动三栏开单区、客户价格档位、欠款额度提醒、订单实时合计、草稿恢复、F5 新建、Escape 清空、送货单预览和浏览器打印。
- 入库开单：可拖动批次录入、商品联想、批次/生产/到期日期、实时金额、草稿恢复、保质期提示和字段级校验。
- 基础档案：商品表格/卡片视图、三档价格和安全库存提示、受控备注/安全库存编辑；客户 VIP/欠款状态；供应商分组信息与 CRUD。
- 库存与退货盘点：批次库存风险、客户/供应商退货伙伴选择与数量上限、盘盈盘亏实时提示、库存分析。
- 行情、定价与报表：行情时间线和本地筛选、外部行情审核、定价模拟毛利预览、周报筛选/打印/CSV 导出。

所有上述界面保留既有后端接口和 SQLite 字段。主题、草稿、表格布局、局部筛选和模拟价格只保存在浏览器本地，不会修改服务端业务数据。

## Prerequisites

- Python 3.11
- Node.js 18 or later

## Clean-clone setup

From the repository root, install the backend and frontend dependencies:

```powershell
pip install -r backend/requirements.txt
npm ci --prefix frontend
```

On Windows, run `start.bat` to initialize the local database and start both services. Open the frontend at http://localhost:8080 and the backend API documentation at http://localhost:8001/docs.

For frontend-only development:

```powershell
Set-Location frontend
npm.cmd run dev
```

The Vite development server listens on http://localhost:8080 by default and proxies existing API requests to the backend.

## Configuration

`SELLHELP_DATABASE_URL` overrides the default SQLite database connection. For example:

```powershell
$env:SELLHELP_DATABASE_URL = "sqlite:///C:/data/sellhelp.db"
```

`SELLHELP_ALLOWED_ORIGINS` is a comma-separated list of browser origins allowed by CORS. It defaults to `http://localhost:8080`:

```powershell
$env:SELLHELP_ALLOWED_ORIGINS = "http://localhost:8080,http://example.local"
```

### External market sync

Configure `ANYSEARCH_API_KEY` only in the backend server environment, then restart the backend for the change to take effect. Do not put this value in the browser, frontend build, or source control.

```powershell
$env:ANYSEARCH_API_KEY = "your-server-side-key"
```

By default, external market data syncs daily at `02:00` in the `Asia/Shanghai` timezone. The schedule can be changed in Settings. Network quotes are always pending review: they affect local market prices and pricing calculations only after an operator manually confirms them.

The sync uses public price-monitoring information from the National Development and Reform Commission, public information from the National Food and Strategic Reserves Administration, and public retail search results. External content can be delayed, incomplete, or promotional, so operators must verify the source and retail context before accepting a quote.

## Verification

Run backend tests:

```powershell
Set-Location backend
python -m pytest -q
```

Run all frontend checks:

```powershell
Set-Location frontend
npm.cmd test
npm.cmd run build
```

Build the frontend only:

```powershell
Set-Location frontend
npm.cmd run build
```

## Backup and recovery

Database backups created by the application are stored under `backend/backup`. The system also creates a pre-restore backup there before a database restore.
