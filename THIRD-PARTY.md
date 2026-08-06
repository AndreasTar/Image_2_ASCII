# Third party software

Image_2_ASCII itself is licensed under the BSD-style licence in [LICENSE](LICENSE). It is
built on the following, which keep their own licences. Both distributed executables include
this file, and the windowed one also carries the full text of the licences that require it.

| Component | Version built against | Licence | Used by |
| :-------- | :-------------------- | :------ | :------ |
| [NumPy](https://numpy.org/) | 2.5.1 | BSD-3-Clause (with 0BSD, MIT, Zlib and CC0-1.0 parts) | both |
| [Pillow](https://python-pillow.org/) | 12.3.0 | MIT-CMU | both |
| [svg.py](https://pypi.org/project/svg.py/) | 1.10.0 | MIT | both |
| [PySide6 / Qt](https://www.qt.io/qt-for-python) | 6.11.1 | LGPL-3.0-only | windowed version only |
| [shiboken6](https://pypi.org/project/shiboken6/) | 6.11.1 | LGPL-3.0-only | windowed version only |

The command line version contains no Qt at all. Only the windowed version does, and only
that download carries the LGPL obligations described below.

## Qt and the LGPL

The windowed version uses the Qt libraries through PySide6 under the **GNU Lesser General
Public License, version 3**. The full text is included beside the executable as
`LGPL-3.0.txt`, together with `GPL-3.0.txt`, which the LGPL builds on and refers to.

Qt is **not** part of this project's own source, and no Qt source has been modified. It is
used as a library, exactly as published on PyPI.

The LGPL requires that whoever receives the program is able to replace those libraries with
their own build of them. **This is why the windowed version ships as a folder rather than as
a single file**: the Qt libraries sit next to the executable as ordinary DLLs, and replacing
one is a matter of overwriting the file. Packing them inside a single executable would have
made that impossible, which is the whole reason the two downloads are shaped differently.

Qt is also available under a commercial licence, which this project does not use.

## Getting the sources

Every component above is published on PyPI and installable with pip. The versions built
against are pinned in the table; the ranges the project accepts are in
[requirements.txt](requirements.txt) and [requirements-gui.txt](requirements-gui.txt).
