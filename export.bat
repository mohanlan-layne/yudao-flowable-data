@echo off
:: 从 BPM 拉取流程到本地
:: 用法:
::   export.bat                        # 全量导出 dev
::   export.bat --env uat              # 全量导出 uat
::   export.bat --env dev pdp_plan_doc_common pdp-review_udit2   # 只拉取指定流程

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

%PYTHON% "%SCRIPT_DIR%scripts\export.py" %*
