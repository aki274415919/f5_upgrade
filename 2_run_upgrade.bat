chcp 65001 >nul
@echo off
setlocal

cd /d "%~dp0"

REM === 检查虚拟环境 ===
if not exist ".venv\Scripts\activate.bat" (
    echo [EN] Python virtual environment not found. Please run prepare_env.bat first!
    echo [JP] Python仮想環境が見つかりません。まず prepare_env.bat を実行してください！
    echo [CN] 未检测到 Python 虚拟环境，请先运行 prepare_env.bat！
    pause
    exit /b 1
)

REM === 激活虚拟环境 ===
call ".venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [EN] Failed to activate Python virtual environment!
    echo [JP] Python仮想環境の有効化に失敗しました！
    echo [CN] Python 虚拟环境激活失败！
    pause
    exit /b 1
)
echo [EN] Python virtual environment activated.
echo [JP] Python仮想環境を有効化しました。

REM === 先跑 3_before_check.py ===
echo [EN] Running pre-check script: 3_before_check.py ...
echo [JP] 事前チェックスクリプトを実行中: 3_before_check.py ...
echo [CN] 正在运行升级前检查脚本: 3_before_check.py ...
python "3_before_check.py"
if errorlevel 1 (
    echo [EN] Pre-check failed! Please check above error.
    echo [JP] 事前チェックに失敗しました。上記エラーをご確認ください。
    echo [CN] 升级前检查失败，请检查上方错误信息。
    pause
    exit /b 1
)

REM === 再跑 upgrade.py ===
echo [EN] Starting F5 upgrade script: upgrade.py ...
echo [JP] F5アップグレードスクリプトを起動します: upgrade.py ...
echo [CN] 开始执行升级主脚本: upgrade.py ...
python "upgrade.py"
if errorlevel 1 (
    echo [EN] Script execution failed! Please check the error message above.
    echo [JP] スクリプト実行に失敗しました。上記のエラーメッセージをご確認ください。
    echo [CN] 脚本运行失败，请检查上方错误信息！
    pause
    exit /b 1
)

echo.
echo [EN] All scripts finished. You may close this window.
echo [JP] すべてのスクリプトが終了しました。このウィンドウを閉じてください。
echo [CN] 所有脚本已执行完毕，可以关闭窗口。
pause
