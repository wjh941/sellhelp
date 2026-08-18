# SellHelp 运维说明

## Windows 桌面安装包

目标系统为 Windows 10/11 x64。发布构建使用
`powershell -ExecutionPolicy Bypass -File scripts\build-desktop.ps1`，生成
`desktop\release\SellHelp Setup 1.0.0.exe`。当前安装包未签名，Windows 可能显示
发布者警告；安装完成后的运行不依赖 Python、Node.js 或网络连接。

卸载程序不会删除 `%LOCALAPPDATA%\SellHelp`，其中保留 SQLite 数据、备份、日志和
桌面 JWT 密钥。要完全清除本地数据，请先退出 SellHelp，然后由当前 Windows 用户显式删除该目录；通常不需要管理员权限。

## 部署启动

后端：进入 `backend` 后执行 `python -m uvicorn app.main:app --host 0.0.0.0 --port 8001`。

前端：进入 `frontend` 后执行 `npm install` 和 `npm run build`；开发环境可执行 `npm run dev`。

生产环境必须设置至少 32 位的 `SELLHELP_JWT_SECRET`，并将 `standalone_mode` 设为 `false` 后再启用多用户登录。

## 角色权限

| 角色 | 权限 |
| --- | --- |
| owner | 管理账户、系统配置、数据库备份恢复、删除业务单据、审计日志和全部导出。 |
| warehouse_operator | 入库、退货、库存查询和盘点；不可删除单据、备份恢复或导出。 |
| sales_clerk | 创建销售单、收款；不可修改库存、系统配置或导出。 |

## SQLite 备份

执行 Alembic 迁移、升级程序或恢复数据前，先停止后端并备份 SQLite 文件：

```powershell
Copy-Item .\backend\yingtai.db .\backend\backup\yingtai_$(Get-Date -Format yyyyMMdd_HHmmss).db
```

确认备份文件可读取后，才能执行 `python -m alembic upgrade head`。Phase4 没有新增数据库迁移。

## Windows PDF 中文

PDF 导出会优先注册 Windows 字体目录中的 `simhei.ttf`、`msyh.ttc` 或 `simsun.ttc`，无法使用时退回 ReportLab 的 `STSong-Light`。部署到 Windows 后应实际下载一份 PDF，确认中文没有方框或乱码。

## 发布检查

- 三个角色分别登录，确认菜单、直接路由和接口权限一致。
- owner 验证 XLSX、PDF、CSV 导出内容完整；非 owner 不应看到导出入口。
- 验证入库、销售、退货、盘点和收款核心流程。
- 验证备份文件可生成，恢复操作仅 owner 可见。
- 检查审计日志包含登录、权限拒绝、配置和导出操作。
- 在目标 Windows 机器验证 PDF 中文字体。

## Windows 桌面版发布验收

- 在未安装 Python、Node.js 且断开网络的 Windows 10/11 x64 机器上安装并启动 EXE，确认本地界面和 `/api` 同源运行。
- 用已有版本安装覆盖升级，确认 `%LOCALAPPDATA%\SellHelp` 中的账号、业务数据、日志和桌面 JWT 密钥保留且可登录。
- 卸载程序后确认 `%LOCALAPPDATA%\SellHelp` 仍存在；只有用户明确删除该目录时才清除本地数据。
- 以 owner 执行备份和恢复，确认恢复后桌面端重启且恢复前自动备份可用。
- 以 owner 验证 XLSX/PDF 导出和打印；检查下载文件非空、PDF 中文字体正常且打印预览内容完整。
- 在生成安装包后执行 `npm.cmd --prefix desktop run test:packaged`；该检查会安装到独立临时目录，验证同源启动、数据持久化、XLSX 导出、后端子进程退出和卸载保留数据。
