@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

:MENU
cls
echo ==========================================================
echo               Media Skills Automation
echo ==========================================================
echo 1. Crawl Hot Topics (NewRank)
echo 2. Generate & Sync to WeChat (Draft Box)
echo 3. Generate & Publish to Xiaohongshu
echo 4. Exit
echo ==========================================================
set /p choice="Please select an option (1-4): "

if "%choice%"=="1" goto CRAWL
if "%choice%"=="2" goto WECHAT
if "%choice%"=="3" goto XIAOHONGSHU
if "%choice%"=="4" goto EXIT

echo Invalid option. Please try again.
pause
goto MENU

:CRAWL
echo.
echo [1] Crawling NewRank Hot Topics...
python -m newrank_skill.crawler
if %errorlevel% neq 0 (
    echo Error occurred during crawling. Check logs/crawler.log.
) else (
    echo Crawling completed. Check output/articles/.
)
pause
goto MENU

:WECHAT
echo.
echo [2] WeChat Automation
echo ----------------------------------------------------------
echo Enter input path (file or directory) [Default: output/articles]:
set /p input_path=
if "%input_path%"=="" set input_path=output/articles

echo.
echo Select mode:
echo 1. Dry Run (Generate only)
echo 2. Sync (Upload to Draft Box)
set /p mode="Select mode (1/2): "

set cmd_args=--input %input_path%

if "%mode%"=="2" (
    set cmd_args=%cmd_args% --sync
) else (
    set cmd_args=%cmd_args% --dry-run
)

echo Running: python wechat_skill/main.py %cmd_args%
python wechat_skill/main.py %cmd_args%

if %errorlevel% neq 0 (
    echo Error occurred. Check logs/wechat.log.
)
pause
goto MENU

:XIAOHONGSHU
echo.
echo [3] Xiaohongshu Automation
echo ----------------------------------------------------------
echo Enter input path (file or directory) [Default: output/articles]:
set /p input_path=
if "%input_path%"=="" set input_path=output/articles

echo.
echo Select mode:
echo 1. Dry Run (Generate only)
echo 2. Publish (Real-time publish)
set /p mode="Select mode (1/2): "

set cmd_args=--input %input_path%

if "%mode%"=="2" (
    echo.
    echo Show browser UI? (y/n) [Default: n]:
    set /p show_ui=
    if "!show_ui!"=="y" set cmd_args=%cmd_args% --non-headless
) else (
    set cmd_args=%cmd_args% --dry-run
)

echo Running: python xiaohongshu_skill/main.py %cmd_args%
python xiaohongshu_skill/main.py %cmd_args%

if %errorlevel% neq 0 (
    echo Error occurred. Check logs/xiaohongshu.log.
)
pause
goto MENU

:EXIT
echo Exiting...
endlocal
exit /b 0
