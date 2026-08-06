# -*- mode: python ; coding: utf-8 -*-
###########################################################################
# Copyright (c) 2024-2026, Andreas Tarasidis (Andy Pandy)                 #
#                                                                         #
# Original repo: https://github.com/AndreasTar/Image_2_ASCII              #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################

# PyInstaller build: the command line tool, as one self contained executable that runs on a
# machine with no Python on it at all.
#
#   pip install -r requirements-dev.txt
#   pyinstaller Image2Ascii.spec --distpath builds/dist --workpath builds/work
#
# The result lands in builds/dist/ and comes out at around 26 MB, most of which is numpy and
# Pillow. This build contains no interface code and no Qt; see Image2AsciiGUI.spec for the
# windowed one, which is a separate download on purpose so that nobody who wants the command
# line tool has to take a hundred megabytes of Qt with it.
#
# What is deliberately left out, and why, is in buildcommon.py.

import sys

sys.path.insert(0, SPECPATH)

from buildcommon import CLI_EXCLUDES, versionResource


analysis = Analysis(
    ['converter.py'],
    pathex = [],
    binaries = [],
    # There is no Qt in this build, so none of the LGPL obligations apply to it. The
    # third party notice still goes in, because numpy, Pillow and svg.py are in here and
    # a single file executable has nowhere else to put it.
    datas = [('THIRD-PARTY.md', '.')],
    hiddenimports = [],
    hookspath = [],
    hooksconfig = {},
    runtime_hooks = [],
    excludes = CLI_EXCLUDES,
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
    version = versionResource('Image2Ascii, command line', 'Image2Ascii.exe'),
    console = True,
    disable_windowed_traceback = False,
    argv_emulation = False,
    target_arch = None,
    codesign_identity = None,
    entitlements_file = None,
)
