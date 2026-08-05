# -*- mode: python ; coding: utf-8 -*-
###########################################################################
# Copyright (c) 2024, Andy Pandy                                          #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################

# PyInstaller build: the windowed tool, engine included.
#
#   pip install -r requirements-dev.txt -r requirements-gui.txt
#   pyinstaller Image2AsciiGUI.spec --distpath builds/dist --workpath builds/work
#
# The result is a folder, builds/dist/Image2Ascii-GUI/, of around 135 MB. Zip that folder
# for release; Image2Ascii-GUI.exe inside it is what users run.
#
# Roughly half of that is Qt and a fifth is numpy's BLAS. It is a lot next to the 28 MB
# command line build, which is the reason the two are separate downloads rather than one.
#
# Two things make this a folder rather than a single file, unlike the command line build:
#
# Qt is LGPL and this project is BSD. Distributing a binary that includes LGPL libraries
# comes with an obligation to let users replace those libraries with their own build. A
# folder satisfies that by construction, because the Qt DLLs sit next to the executable and
# can simply be swapped. Packing them inside a single file does not.
#
# It also starts noticeably faster. A one-file build unpacks its whole payload to a
# temporary folder on every launch, and unpacking Qt is not quick.
#
# console = False is what makes this a windowed application: no terminal appears behind it
# when it is double clicked. The consequence is that stdout does not exist, so nothing here
# may print. Everything the engine would have printed is routed to the log pane instead,
# through the `log` callback on the config.

import sys

sys.path.insert(0, SPECPATH)

from buildcommon import GUI_EXCLUDES, keepBinary


analysis = Analysis(
    ['converter_gui.py'],
    pathex = [],
    binaries = [],
    datas = [],
    hiddenimports = [],
    hookspath = [],
    hooksconfig = {
        # Qt's plugins are found at runtime rather than imported, so excluding the Python
        # modules above does not remove them. These are the families a widget application
        # that shows pictures has no use for.
        'pyside6': {
            'exclude_plugins': [
                'qmltooling', 'scenegraph', 'assetimporters', 'sqldrivers',
                'multimedia', 'position', 'sensors', 'texttospeech', 'webview',
            ],
        },
    },
    runtime_hooks = [],
    excludes = GUI_EXCLUDES,
    noarchive = False,
)

# Done after the analysis rather than through `excludes`, because these arrive as collected
# binaries rather than as imports and `excludes` never sees them. See buildcommon.py.
analysis.binaries = [entry for entry in analysis.binaries if keepBinary(entry)]

pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries = True,
    name = 'Image2Ascii-GUI',
    debug = False,
    bootloader_ignore_signals = False,
    strip = False,
    upx = True,
    upx_exclude = [],
    # No terminal window. The interface is the interface.
    console = False,
    # Left on, so that a crash still surfaces a dialog. With no console to print to, the
    # alternative is a windowed build that vanishes silently.
    disable_windowed_traceback = False,
    argv_emulation = False,
    target_arch = None,
    codesign_identity = None,
    entitlements_file = None,
)

collected = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip = False,
    upx = True,
    upx_exclude = [],
    name = 'Image2Ascii-GUI',
)
