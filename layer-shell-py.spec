# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


gtk4_layer_shell_typelibs = [
    (str(path), "gi_typelibs")
    for path in (
        Path("/usr/lib/girepository-1.0/Gtk4LayerShell-1.0.typelib"),
        Path("/usr/lib64/girepository-1.0/Gtk4LayerShell-1.0.typelib"),
    )
    if path.exists()
]

a = Analysis(
    ["scripts/pyinstaller_entry.py"],
    pathex=["src"],
    binaries=[],
    datas=gtk4_layer_shell_typelibs,
    hiddenimports=[
        "gi",
        "gi.repository.Gdk",
        "gi.repository.Gtk",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="layer-shell-py",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
