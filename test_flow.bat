@echo off
:: 端到端流程测试
:: 用法:
::   test_flow.bat <flow_key> <executor_user_id> <charge_user_id>
::   test_flow.bat --env uat pdp_plan_doc_common 2637 1

setlocal
set SCRIPT_DIR=%~dp0

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

%PYTHON% "%SCRIPT_DIR%scripts\test_flow.py" %*
