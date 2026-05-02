@echo off
REM ============================================================
REM Foundry VTT NPC Builder - локальный запуск под Windows
REM
REM При первом запуске:
REM   1. Проверяет, что установлен Python 3.10+
REM   2. Создаёт виртуальное окружение в папке .venv
REM   3. Ставит зависимости из requirements.txt
REM
REM При последующих запусках просто стартует Streamlit
REM и открывает браузер на http://localhost:8501.
REM ============================================================

setlocal
cd /d "%~dp0"

REM --- ищем Python ---
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python не найден в PATH.
    echo Скачайте Python 3.10+ с https://www.python.org/downloads/
    echo и обязательно отметьте "Add Python to PATH" при установке.
    pause
    exit /b 1
)

REM --- создаём venv, если ещё нет ---
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Создаю виртуальное окружение .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Не удалось создать venv.
        pause
        exit /b 1
    )

    echo [INFO] Устанавливаю зависимости ...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Не удалось установить зависимости.
        pause
        exit /b 1
    )
)

REM --- запускаем Streamlit ---
echo [INFO] Запускаю Foundry NPC Builder на http://localhost:8501
".venv\Scripts\python.exe" -m streamlit run app.py --server.headless=false --browser.gatherUsageStats=false

endlocal
