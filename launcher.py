"""Точка входа для сборки одиночного исполняемого файла через PyInstaller.

Использовать только если хочется получить .exe без установленного Python.
Для повседневного запуска удобнее run.bat / run.sh.
"""
import os
import sys

from streamlit.web import cli as stcli


def main() -> None:
    # При запуске из PyInstaller-onefile ресурсы распакованы в sys._MEIPASS
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    app_path = os.path.join(base, "app.py")

    sys.argv = [
        "streamlit", "run", app_path,
        "--server.headless=false",
        "--browser.gatherUsageStats=false",
    ]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
