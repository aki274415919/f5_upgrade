chcp 65001 >nul
@echo off
setlocal enabledelayedexpansion

set "PY_VER=3.11.9"
set "PY_MAJOR=3"
set "PY_MINOR=11"
set "PY_INSTALLER=python-installer.exe"
set "PY_URL=https://www.python.org/ftp/python/%PY_VER%/python-%PY_VER%-amd64.exe"
set "VENV_DIR=.venv"
set "SCRIPT_FILE=upgrade.py"

REM =========================
REM 检查 Python 是否存在
REM =========================
where python >nul 2>nul
if %errorlevel% neq 0 (
    goto :InstallPython
)

REM =========================
REM 检查 Python 版本
REM =========================
for /f "tokens=2 delims= " %%a in ('python --version 2^>^&1') do set "CUR_PY_VER=%%a"
for /f "tokens=1,2 delims=." %%a in ("!CUR_PY_VER!") do (
    set "CUR_MAJOR=%%a"
    set "CUR_MINOR=%%b"
)
if "!CUR_MAJOR!"=="3" if !CUR_MINOR! LSS %PY_MINOR% (
    echo [EN] Python version is too old: !CUR_PY_VER!
    goto :InstallPython
)

goto :CreateVenv

:InstallPython
echo ---------------------------------------------
echo [EN] Python not found or too old.
echo [CN] 未检测到 Python 或版本过低。
echo [JP] Pythonが見つからない、または古すぎます。
echo.
echo [EN] Downloading Python %PY_VER% installer...
echo [JP] Python %PY_VER% のインストーラーをダウンロード中...
echo.

powershell -Command "Invoke-WebRequest -Uri '%PY_URL%' -OutFile '%PY_INSTALLER%'"
if not exist "%PY_INSTALLER%" (
    echo [EN] Download failed! Please download manually: %PY_URL%
    echo [CN] 下载失败，请手动访问：%PY_URL%
    echo [JP] ダウンロード失敗：%PY_URL%
    pause
    exit /b 1
)

echo [EN] Installing Python %PY_VER% silently...
echo [CN] 正在静默安装 Python...
echo [JP] Pythonをサイレントインストール中...
"%PY_INSTALLER%" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0

if %errorlevel% neq 0 (
    echo [EN] Python installation failed!
    echo [CN] Python 安装失败！
    echo [JP] Pythonのインストールに失敗しました！
    pause
    exit /b 1
)

REM 刷新 PATH
set PATH=%ProgramFiles%\Python%PY_MAJOR%%PY_MINOR%;%ProgramFiles%\Python%PY_MAJOR%%PY_MINOR%\Scripts;%PATH%
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [EN] Python not found even after install.
    pause
    exit /b 1
)

:CreateVenv
REM =========================
REM 创建虚拟环境
REM =========================
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [EN] Creating Python virtual environment...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [EN] Virtual environment creation failed!
        pause
        exit /b 1
    )
) else (
    echo [EN] Python virtual environment already exists. Skipping creation.
)

REM =========================
REM 激活虚拟环境
REM =========================
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo [EN] Virtual environment activation failed!
    pause
    exit /b 1
)

REM =========================
REM 升级 pip setuptools
REM =========================
echo [EN] Upgrading pip and setuptools...
python -m pip install --upgrade pip setuptools
if errorlevel 1 (
    echo [EN] pip/setuptools upgrade failed!
    pause
    exit /b 1
)

REM =========================
REM 安装依赖
REM =========================
echo [EN] Installing dependencies (paramiko pillow)...
python -m pip install paramiko pillow
if errorlevel 1 (
    echo [EN] Dependency installation failed.
    pause
    exit /b 1
)

REM =========================
REM 测试依赖
REM =========================
python -c "import paramiko; import tkinter; import PIL; print('[EN] All dependencies OK')"
if errorlevel 1 (
    echo [EN] Import test failed. Please check manually.
    pause
    exit /b 1
)

echo.
echo [EN] Python virtual environment and dependencies are ready!
echo [JP] Python仮想環境と依存関係が準備できました！
echo [CN] Python 虚拟环境和依赖库准备完毕！
pause
exit /b 0
