#!/usr/bin/env bash
# ============================================================
# Foundry VTT NPC Builder — локальный запуск под macOS / Linux
#
# При первом запуске создаёт venv и ставит зависимости.
# При последующих просто стартует Streamlit на http://localhost:8501.
# ============================================================
set -e

cd "$(dirname "$0")"

# --- ищем python ---
if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "[ERROR] Python не найден. Установите Python 3.10+ и повторите запуск."
    exit 1
fi

# --- venv ---
if [ ! -x ".venv/bin/python" ]; then
    echo "[INFO] Создаю виртуальное окружение .venv ..."
    "$PY" -m venv .venv
    echo "[INFO] Устанавливаю зависимости ..."
    .venv/bin/python -m pip install --upgrade pip
    .venv/bin/python -m pip install -r requirements.txt
fi

# --- запуск ---
echo "[INFO] Запускаю Foundry NPC Builder на http://localhost:8501"
exec .venv/bin/python -m streamlit run app.py \
    --server.headless=false \
    --browser.gatherUsageStats=false
