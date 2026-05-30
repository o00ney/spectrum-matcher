# -*- mode: python ; coding: utf-8 -*-

"""
PyInstaller spec for NMR Spectrum Matcher client.
Build with: pyinstaller spectrum-matcher.spec
"""

import sys
from pathlib import Path

# SPECPATH is provided by PyInstaller; fallback for IDE inspection
_root = Path(SPECPATH if 'SPECPATH' in dir() else '.').resolve()

a = Analysis(
    [str(_root / 'spectrum_matcher_client' / '__main__.py')],
    pathex=[str(_root)],
    binaries=[],
    datas=[
        (str(_root / 'spectrum_matcher_client'), 'spectrum_matcher_client'),
    ],
    hiddenimports=[
        'matplotlib.backends.backend_qtagg',
        'matplotlib.backends.backend_qt5agg',
        'matplotlib.backends.backend_agg',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'shiboken6',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'tcl',
        'wx',
        'IPython',
        'jupyter',
        'notebook',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='NMR-Spectrum-Matcher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(_root / 'spectrum_matcher_client' / 'icon.ico') if (Path(_root) / 'spectrum_matcher_client' / 'icon.ico').exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='NMR-Spectrum-Matcher',
)
