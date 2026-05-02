# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec для Foundry VTT NPC Builder.

Собирает однофайловый исполняемый модуль launcher.py со всеми ресурсами
Streamlit, справочниками data/ и шаблоном templates/.

Сборка:
    pyinstaller FoundryNPCBuilder.spec --clean --noconfirm

Запускать на ТОЙ ОС, под которую нужен бинарь:
    Windows  → FoundryNPCBuilder.exe
    macOS    → FoundryNPCBuilder.app / FoundryNPCBuilder
    Linux    → FoundryNPCBuilder
"""

from PyInstaller.utils.hooks import (
    collect_all,
    collect_data_files,
    collect_submodules,
    copy_metadata,
)

# Streamlit — самая капризная часть: нужны и метаданные, и data-файлы,
# и куча скрытых импортов рантайма.
streamlit_datas, streamlit_binaries, streamlit_hidden = collect_all("streamlit")
altair_datas, altair_binaries, altair_hidden = collect_all("altair")

# Метаданные для importlib_metadata-проверок внутри Streamlit
metadata = []
for pkg in (
    "streamlit",
    "altair",
    "pandas",
    "numpy",
    "pyarrow",
    "pillow",
    "protobuf",
    "click",
    "tornado",
    "blinker",
    "gitpython",
    "watchdog",
):
    try:
        metadata += copy_metadata(pkg)
    except Exception:
        # Не все пакеты могут оказаться установлены — это нормально.
        pass

datas = [
    ("app.py", "."),
    ("data", "data"),
    ("templates", "templates"),
    (".streamlit", ".streamlit"),
] + streamlit_datas + altair_datas + metadata

hiddenimports = (
    streamlit_hidden
    + altair_hidden
    + collect_submodules("streamlit.runtime")
    + collect_submodules("streamlit.web")
    + [
        "streamlit.runtime.scriptrunner.magic_funcs",
        "importlib_metadata",
    ]
)

binaries = streamlit_binaries + altair_binaries

block_cipher = None

a = Analysis(
    ["launcher.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="FoundryNPCBuilder",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,             # оставляем консоль, чтобы видеть логи Streamlit
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
