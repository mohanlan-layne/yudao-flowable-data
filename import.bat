@echo off
:: 推送本地流程到 BPM
:: 用法:
::   import.bat                                       # 全量推送到 dev
::   import.bat --env prod                            # 全量推送到 prod
::   import.bat pdp_plan_doc_common                  # 推送单个流程
::   import.bat pdp_plan_doc_common pdp_plan_doc_dfm # 推送多个流程
::   import.bat --env prod pdp_plan_doc_common        # 指定环境 + 指定流程

setlocal
set SCRIPT_DIR=%~dp0

:: 检测 Python
set PYTHON=
for %%c in (python3 python) do (
    if not defined PYTHON (
        %%c --version >nul 2>&1 && set PYTHON=%%c
    )
)

if not defined PYTHON (
    echo [提示] 未检测到 Python，正在尝试通过 winget 安装...
    winget install -e --id Python.Python.3 --silent
    if errorlevel 1 (
        echo [错误] 自动安装失败，请手动安装 Python 3：
        echo   https://www.python.org/downloads/
        pause
        exit /b 1
    )
    set PYTHON=python
)

%PYTHON% "%SCRIPT_DIR%scripts\import.py" %*
