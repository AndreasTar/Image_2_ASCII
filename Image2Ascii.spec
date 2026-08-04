# -*- mode: python ; coding: utf-8 -*-
###########################################################################
# Copyright (c) 2024, Andy Pandy                                          #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################

# PyInstaller build: one self contained executable that runs on a machine with no Python
# on it at all.
#
#   pip install -r requirements-dev.txt
#   pyinstaller Image2Ascii.spec
#
# The result lands in dist/. Expect roughly 50-60 MB, most of which is numpy and Pillow.
#
# The GPU and video libraries are excluded on purpose. They are optional at runtime, each
# is far larger than everything else here put together, and a frozen build cannot see the
# system's site-packages anyway. --gpu inside the executable therefore reports that no GPU
# library is present and carries on using the CPU, which is exactly what it does on any
# machine without one installed.
#
# Video still works in the frozen build if an `ffmpeg` binary is on the PATH, because that
# path is a subprocess rather than an import. Animated GIF, WebP and APNG need nothing at
# all, since Pillow is bundled.

EXCLUDED_PACKAGES = [
    'torch', 'cupy', 'cupy_backends',           # optional GPU backends, see above
    'av', 'imageio', 'imageio_ffmpeg',          # optional video decoders, see above
    'tkinter', 'PIL.ImageTk', 'PIL.ImageQt',    # no GUI in a command line tool
    'matplotlib', 'scipy', 'pandas',
    'pytest', '_pytest', 'IPython',
    # pkg_resources has to go with setuptools. Excluding setuptools on its own leaves
    # PyInstaller's pkg_resources runtime hook in the build, which then fails at startup
    # looking for the setuptools vendored packages that are no longer there.
    'setuptools', 'pkg_resources', 'pip',
]


analysis = Analysis(
    ['converter.py'],
    pathex = [],
    binaries = [],
    datas = [],
    hiddenimports = [],
    hookspath = [],
    hooksconfig = {},
    runtime_hooks = [],
    excludes = EXCLUDED_PACKAGES,
    noarchive = False,
)

pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name = 'Image2Ascii',
    debug = False,
    bootloader_ignore_signals = False,
    strip = False,
    upx = True,
    upx_exclude = [],
    runtime_tmpdir = None,
    console = True,
    disable_windowed_traceback = False,
    argv_emulation = False,
    target_arch = None,
    codesign_identity = None,
    entitlements_file = None,
)
