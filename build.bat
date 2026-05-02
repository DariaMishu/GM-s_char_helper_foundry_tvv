@echo off
REM ============================================================
REM Сборка FoundryNPCBuilder.exe (Windows)
REM
REM Запускать на Windows-машине с установленным Python 3.10+.
REM Результат: dist\FoundryNPCBuilder.exe
REM ============================================================

setlocal
cd /d "%~dp0"

REM --- Python ---
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python не найден в PATH. Установите Python 3.10+.
    pause
    exit /b 1
)

REM --- venv ---
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Создаю виртуальное окружение .venv ...
    python -m venv .venv
)

echo [INFO] Обновляю pip и ставлю зависимости + pyinstaller ...
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

echo [INFO] Чищу прошлые сборки ...
if exist build  rmdir /s /q build
if exist dist   rmdir /s /q dist

echo [INFO] Собираю FoundryNPCBuilder.exe ...
pyinstaller FoundryNPCBuilder.spec --clean --noconfirm
if errorlevel 1 (
    echo [ERROR] Сборка завершилась с ошибкой.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Готово! Бинарь лежит здесь:
echo   %CD%\dist\FoundryNPCBuilder.exe
echo Запустите его двойным кликом — откроется браузер на
echo http://localhost:8501.
echo ============================================================
pause
endlocal
