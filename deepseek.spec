# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['psychic.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
# Qt on Windows 11 uses the system ICU DLL. A different ICU from PATH
# (for example Poppler's) has incompatible exports and prevents QtCore loading.
a.binaries = [entry for entry in a.binaries
              if entry[0].lower() != 'icuuc.dll']
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='psychic',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='psychic',
)
