@echo off
REM 啟動媒體風向監測儀表板和排程爬蟲
REM 使用統一的 Python 環境 (.venv-1)

setlocal enabledelayedexpansion

REM 檢查是否已啟動相同程序
tasklist /FI "WINDOWTITLE eq News Crawler UI" 2>NUL | find /I /N "cmd.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo News Crawler UI 已在運行
) else (
    echo 啟動 News Crawler UI...
    start "News Crawler UI" cmd /k "cd /d %~dp0 && .\.venv-1\Scripts\python.exe news_crawler-main\dashboard.py"
)

REM 等待 1 秒
timeout /t 1 /nobreak

tasklist /FI "WINDOWTITLE eq Media Dashboard" 2>NUL | find /I /N "cmd.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo Media Dashboard 已在運行
) else (
    echo 啟動 Media Dashboard...
    start "Media Dashboard" cmd /k "cd /d %~dp0 && .\.venv-1\Scripts\python.exe media_dashboard\app.py"
)

REM 等待 1 秒
timeout /t 1 /nobreak

tasklist /FI "WINDOWTITLE eq Pipeline Scheduler" 2>NUL | find /I /N "cmd.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo Pipeline Scheduler 已在運行
) else (
    echo 啟動 Pipeline Scheduler...
    start "Pipeline Scheduler" cmd /k "cd /d %~dp0 && .\.venv-1\Scripts\python.exe pipeline\scheduler.py"
)

REM 等待服務啟動
timeout /t 3 /nobreak

REM 開啟瀏覽器頁面
echo 開啟瀏覽器...
start "" "http://127.0.0.1:8000/"
timeout /t 1 /nobreak
start "" "http://127.0.0.1:5000/"

echo.
echo ===================================================
echo 已啟動所有服務：
echo - News Crawler UI: http://127.0.0.1:8000/
echo - Media Dashboard: http://127.0.0.1:5000/
echo - Pipeline Scheduler: 後台運行（4 小時執行一次）
echo ===================================================
echo.
echo 如果網頁尚未出現，請手動開啟瀏覽器並訪問上述地址。
echo 按任意鍵繼續...
pause