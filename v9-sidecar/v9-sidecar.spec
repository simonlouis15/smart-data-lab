# -*- mode: python ; coding: utf-8 -*-

# vd_sensor and hc_measurement are imported lazily (inside cli.vd_controls /
# cli.hc_controls), so PyInstaller's static analysis won't see them -- list them
# explicitly. The SDKs they use (XtalX for vd; nidaqmx for hc) are also lazy
# imports; pull in everything they need when installed in the build env, and
# degrade gracefully (the subcommand still errors cleanly at runtime) when not.
hiddenimports = ['vd_sensor', 'hc_measurement']
datas = []
binaries = []

try:
    from PyInstaller.utils.hooks import collect_all

    for _pkg in ('xtalx', 'libusb_package', 'nidaqmx'):
        try:
            _datas, _binaries, _hidden = collect_all(_pkg)
            datas += _datas
            binaries += _binaries
            hiddenimports += _hidden
        except Exception:
            pass
except Exception:
    pass


a = Analysis(
    ['cli.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='v9-sidecar',
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
