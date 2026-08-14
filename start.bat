@echo off
chcp 65001
title 盈泰副食贸易管理系统 - 一键启动

echo ============================================
echo   盈泰副食贸易管理系统
echo   专为东莞高埗新联综合市场定制
echo ============================================
echo.

REM 检查 Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 检查 Node.js
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Node.js，请先安装 Node.js 18+
    echo 下载地址: https://nodejs.org/
    pause
    exit /b 1
)

echo [1/5] 正在安装后端依赖...
cd /d "%~dp0backend"
pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo [错误] 后端依赖安装失败
    pause
    exit /b 1
)
echo       ✓ 后端依赖安装完成

echo.
echo [2/5] 正在初始化数据库...
python -c "from app.database import init_db; init_db()"
if %errorlevel% neq 0 (
    echo [错误] 数据库初始化失败
    pause
    exit /b 1
)
echo       ✓ 数据库初始化完成

echo.
echo [3/5] 正在创建初始数据...
python -c "
import sys
sys.path.insert(0, '.')
from app.init_data import main
main()
"
echo       ✓ 初始数据创建完成

echo.
echo [4/5] 正在安装前端依赖...
cd /d "%~dp0frontend"
if not exist node_modules (
    npm install
    if %errorlevel% neq 0 (
        echo [错误] 前端依赖安装失败
        pause
        exit /b 1
    )
) else (
    echo       前端依赖已安装，跳过
)

echo.
echo [5/5] 正在启动系统...
echo.
echo ============================================
echo   系统启动中，请在浏览器访问：
echo   前端：http://localhost:8080
echo   后端API：http://localhost:8001/docs
echo ============================================
echo.

REM 启动后端（后台）
cd /d "%~dp0backend"
start "盈泰后端" cmd /k "python -m uvicorn app.main:app --host 0.0.0.0 --port 8001"

REM 等待2秒后启动前端
timeout /t 2 /nobreak >nul

cd /d "%~dp0frontend"
start "盈泰前端" cmd /k "npm run dev -- --port 8080"

echo.
echo 系统已在新窗口中启动！
echo 如无法访问，请检查端口 8080 和 8001 是否被占用。
echo.
pause
