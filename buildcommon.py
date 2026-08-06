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

# What both builds leave out.
#
# There are two executables and one engine between them, so this list exists to stop the
# two spec files drifting apart. Whenever a dependency is added to the tool, the decision
# about whether it belongs in a frozen build gets made once, here, rather than twice.
#
# Imported by the spec files, which are ordinary Python but do not have their own folder on
# the import path, so each one puts SPECPATH there first:
#
#   import sys; sys.path.insert(0, SPECPATH)
#   from buildcommon import ...
#
# Nothing in here is imported by the tool itself.

# Optional at runtime and far larger than everything else put together. A frozen build
# cannot see the host's site-packages anyway, so --gpu inside either executable reports that
# no GPU library is present and carries on using the CPU, which is exactly what it does on
# any machine without one installed.
OPTIONAL_ACCELERATORS = [
    'torch', 'cupy', 'cupy_backends',
]

# Video decoding and encoding. Left out for the same reason, and video still works in either
# frozen build if an `ffmpeg` binary is on the PATH, because that path is a subprocess
# rather than an import. Animated GIF, WebP and APNG need nothing at all, since Pillow is
# bundled.
OPTIONAL_VIDEO = [
    'av', 'imageio', 'imageio_ffmpeg',
]

# Never used by either frontend, but reachable from something that is.
DEVELOPMENT_ONLY = [
    'matplotlib', 'scipy', 'pandas',
    'pytest', '_pytest', 'IPython',
    # pkg_resources has to go with setuptools. Excluding setuptools on its own leaves
    # PyInstaller's pkg_resources runtime hook in the build, which then fails at startup
    # looking for the setuptools vendored packages that are no longer there.
    'setuptools', 'pkg_resources', 'pip',
]

# Tk is never wanted. The GUI is Qt, and the command line has no interface at all, so this
# is common to both. `PIL.ImageQt` goes too: the GUI hands pictures to Qt as PNG bytes
# rather than through Pillow's Qt bridge, precisely so that neither build depends on Pillow
# having been built against a particular binding.
NO_OTHER_TOOLKITS = [
    'tkinter', 'PIL.ImageTk', 'PIL.ImageQt',
]

COMMON_EXCLUDES = (
    OPTIONAL_ACCELERATORS + OPTIONAL_VIDEO + DEVELOPMENT_ONLY + NO_OTHER_TOOLKITS
)

# The command line build must contain no interface code whatsoever. `converter.py` does not
# import `gui`, so none of this would be pulled in regardless; naming it makes that a
# guarantee rather than a happy consequence of nobody having added a stray import yet.
CLI_EXCLUDES = COMMON_EXCLUDES + [
    'gui', 'PySide6', 'shiboken6',
]

# Qt ships far more than a desktop window needs, and PyInstaller bundles whatever it can
# reach. Dropping these is the difference between roughly 200 MB and roughly 80 MB; none of
# them is reachable from a QWidget application that draws pictures and text.
UNUSED_QT_MODULES = [
    'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtWebEngineQuick',
    'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtQuick3D', 'PySide6.QtQuickWidgets',
    'PySide6.Qt3DCore', 'PySide6.Qt3DRender', 'PySide6.Qt3DInput', 'PySide6.Qt3DLogic',
    'PySide6.Qt3DAnimation', 'PySide6.Qt3DExtras',
    'PySide6.QtCharts', 'PySide6.QtDataVisualization', 'PySide6.QtGraphs',
    'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets', 'PySide6.QtSpatialAudio',
    'PySide6.QtSql', 'PySide6.QtTest', 'PySide6.QtDesigner', 'PySide6.QtUiTools',
    'PySide6.QtHelp', 'PySide6.QtBluetooth', 'PySide6.QtNfc',
    'PySide6.QtPositioning', 'PySide6.QtLocation', 'PySide6.QtSerialPort',
    'PySide6.QtSensors', 'PySide6.QtPdf', 'PySide6.QtPdfWidgets',
    'PySide6.QtScxml', 'PySide6.QtRemoteObjects', 'PySide6.QtTextToSpeech',
    'PySide6.QtWebChannel', 'PySide6.QtWebSockets', 'PySide6.QtHttpServer',
]

GUI_EXCLUDES = COMMON_EXCLUDES + UNUSED_QT_MODULES

# Excluding the Python modules above is not enough on its own.
#
# PyInstaller's PySide6 hook collects Qt's shared libraries as *binaries*, worked out from
# what it finds in the package rather than from what the program imports. `excludes` only
# governs imports, so the DLLs behind the modules above are still copied in. Measured on a
# first build: the QML engine, the PDF renderer and Qt's bundled OpenSSL together came to
# about 30 MB of libraries that a widget application which draws pictures cannot reach.
#
# They are dropped by filtering `analysis.binaries` in the spec instead. Matching is on the
# start of the file name, so a family goes in one entry.
#
# Two large files are deliberately *not* here:
#
#   opengl32sw.dll (~20 MB) is Qt's software OpenGL fallback. Nothing here asks for OpenGL,
#   but Qt reaches for this when a machine has no usable GPU driver, a virtual machine, or
#   a remote desktop session, and without it the window fails to appear at all. Twenty
#   megabytes is a great deal cheaper than not starting.
#
#   The OpenBLAS library under numpy.libs (~20 MB) is what numpy does its arithmetic with.
#   The command line build carries it too.
UNUSED_QT_LIBRARIES = [
    'qt6quick',         # the QML runtime, in all its parts
    'qt6qml',
    'qt6pdf',
    'libcrypto',        # Qt's OpenSSL, for TLS this program never opens a socket to use
    'libssl',
]


# What Explorer shows under Properties, and what an antivirus vendor or a curious user looks
# at first to decide whether a downloaded executable is what it claims to be. Without one
# both files report themselves as version 0.0.0.0 with no name and no author, which is not
# in itself suspicious but does nothing to help.
#
# This does not make SmartScreen quiet. Only a signing certificate does that.
PRODUCT_NAME = 'Image2Ascii'
COMPANY_NAME = 'Andreas Tarasidis'
COPYRIGHT = 'Copyright (c) 2024-2026 Andreas Tarasidis. BSD 3-Clause licence.'


def versionResource(description: str, filename: str):
    """
    The Windows version resource for one of the two executables.

    Built from `tools.APP_VERSION` rather than written down again, so that the number
    Explorer reports and the number `--version` prints cannot disagree. Imported inside the
    function because the spec file only puts the repository on the path just before calling
    this, and `tools` pulls in nothing heavier than the standard library.
    """
    from PyInstaller.utils.win32.versioninfo import (
        FixedFileInfo, StringFileInfo, StringStruct, StringTable,
        VarFileInfo, VarStruct, VSVersionInfo,
    )

    from src.tools import APP_VERSION

    # The resource wants exactly four numbers; the project uses three.
    numbers = tuple(int(part) for part in APP_VERSION.split('.'))
    numbers = (numbers + (0, 0, 0, 0))[:4]

    return VSVersionInfo(
        ffi = FixedFileInfo(
            filevers = numbers,
            prodvers = numbers,
            mask = 0x3F,
            flags = 0x0,
            OS = 0x40004,       # Windows NT, 32 bit Windows subsystem
            fileType = 0x1,     # an application
            subtype = 0x0,
            date = (0, 0),
        ),
        kids = [
            # 0409 is US English and 04B0 is Unicode. The two have to agree with the
            # Translation entry below or Explorer shows nothing at all.
            StringFileInfo([StringTable('040904B0', [
                StringStruct('CompanyName', COMPANY_NAME),
                StringStruct('FileDescription', description),
                StringStruct('FileVersion', APP_VERSION),
                StringStruct('InternalName', filename),
                StringStruct('LegalCopyright', COPYRIGHT),
                StringStruct('OriginalFilename', filename),
                StringStruct('ProductName', PRODUCT_NAME),
                StringStruct('ProductVersion', APP_VERSION),
            ])]),
            VarFileInfo([VarStruct('Translation', [0x0409, 1200])]),
        ],
    )


def keepBinary(entry) -> bool:
    """
    Whether one collected binary belongs in the windowed build.

    Handed to `filter` over `analysis.binaries`, where each entry's first field is the name
    the file will have inside the bundle.
    """
    import os

    name = os.path.basename(entry[0]).lower()

    return not any(name.startswith(prefix) for prefix in UNUSED_QT_LIBRARIES)
