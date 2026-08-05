###########################################################################
# Copyright (c) 2024, Andy Pandy                                          #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################

"""
The graphical way in, next to `converter.py`'s command line one.

Named after the tool rather than simply `gui.py`, because a module and a package cannot
share a name in the same folder: `gui/` is the package, and a `gui.py` beside it would be
shadowed by it on import.

Kept deliberately thin. Everything it does lives in `gui.app`, so that failing to find Qt
is reported as a sentence rather than as a traceback, which is the one thing that has to
work before there is a window to report anything in.
"""

import sys


def main() -> int:
    try:
        from gui.app import run
    except ImportError as e:
        print(
            "\nImage2Ascii could not start its interface.\n\n"
            f"\t{e}\n\n"
            "The graphical version needs PySide6, which the command line version does not:\n"
            "\tpip install -r requirements-gui.txt\n\n"
            "The command line version is unaffected and still runs:\n"
            "\tpython converter.py --help\n",
            file = sys.stderr,
        )
        return 1

    return run(sys.argv)


if __name__ == '__main__':
    sys.exit(main())
