###########################################################################
# Copyright (c) 2024, Andy Pandy                                          #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################

# Project inspired by this tutorial:
# https://www.geeksforgeeks.org/converting-image-ascii-image-python/
# More details at:
# https://en.wikipedia.org/wiki/ASCII_art#:~:text=of%20Unicode.-,Methods%20for%20generating%20ASCII%20art

import sys

from src import frontend
from src.tools import APP_VERSION


def prepareConsole() -> None:
    """
    Makes the terminal able to show what this tool produces.

    Two things are needed, both Windows problems in practice:

    The console's default encoding is a legacy code page, cp1252 on a typical Windows
    install, which cannot represent a single braille or block character. Printing one
    raises UnicodeEncodeError and takes the whole run down with it, so standard output is
    switched to UTF-8 first. `errors='replace'` means a terminal that still cannot cope
    shows placeholder characters rather than losing the output entirely.

    ANSI escape sequences are also ignored by the Windows console until virtual terminal
    processing is switched on, which makes coloured output and animation playback appear
    as raw escape codes. Enabling it needs one call into the Windows API, which is done
    here through ctypes rather than by taking on a dependency for it.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding = 'utf-8', errors = 'replace')
        except (AttributeError, ValueError, OSError):
            # Already suitable, or redirected somewhere that cannot be reconfigured.
            pass

    if sys.platform != 'win32':
        return

    try:
        import ctypes

        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        STD_OUTPUT_HANDLE = -11

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        mode = ctypes.c_uint32()

        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING)
    except Exception:
        # Not a real console, or an old Windows without the flag. Colour will not show,
        # which is worth carrying on without.
        pass


def main():
    prepareConsole()

    print(f"\n{'=-=-'*18}")
    print(f"\
\n`Image2Ascii` tool, version: {APP_VERSION}\n\n\
Copyright holder and creator: Andreas Tarasidis\nGithub Link: https://github.com/AndreasTar \n\
Repository Link: https://github.com/AndreasTar/Image_2_ASCII \n\
Licensed under the BSD-style license found in the LICENSE file of the root directory.\n"
    )
    print(f"{'=-=-'*18}\n")
    
    print("Starting tool...")
    frontend.setupParser()
    frontend.runTool()
    print("\nTool finished with no errors!\n")

	

if __name__ == '__main__':
	main()
