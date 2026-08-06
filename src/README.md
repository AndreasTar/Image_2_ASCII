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

This readme will just explain the general layout of the source code, and the responsibilites of each file,
and also will contain the TODO list for internal operations.

The flow through the tool is one direction only, and there are two ways in:

    converter.py     -> frontend --\
                                    >-- config -> midend -> backend -> compute
    converter_gui.py -> ../gui  --/                 |           \--> converters
                                                    \--> sources

Both frontends do the same job in different words: work out what the user wants, put it in a
`Config`, and hand that to the midend. Neither knows the other exists, and nothing in `src`
imports `gui`, which is what lets the command line build into an executable with no Qt in it.

### converter.py
Tells **frontend** to make the parser and then run\
Also gets the result, error or ascii, and shows it on screen or returns it

### converter_gui.py and ../gui
The windowed frontend, needing PySide6 which the command line does not\
Same job as **frontend**, reading widgets instead of flags, and previewing instead of prompting\
`gui/session.py` is the part that builds the `Config`, and imports no Qt so it can be tested headlessly

### frontend
Holds parser, and prolly not use it much after initialisation\
Makes parser, handles return and error\
Surface checks if flags are ok, and either asks user for input or errors\
Builds a `Config` holding everything the conversion needs, and hands it to the midend\
This is the only file that reads arguments or talks to the user in a terminal

### config
What a conversion *is*, with no opinion about who asked for it\
Holds the `Config` itself, the rules about which combinations can produce a file, and the
choosing of a character set\
Lives here rather than in **frontend** so that both frontends enforce the same rules, and so
that adding a character set only has to be taught to one place\
Also carries the `progress` and `log` callbacks, which are how the midend reports to a window
instead of to a terminal, and `embedColor`, which is how a caller with nothing to prompt
*through* answers the one question the midend would otherwise ask

### sources
Turns whatever the input file is into a sequence of frames\
A still image is one frame, an animated GIF is several, a video is a great many, and nothing
downstream has to care which\
Animated GIF, WebP and APNG need no extra dependency because Pillow reads them already;
video needs one of PyAV, imageio-ffmpeg or an ffmpeg binary, resolved the same lazy way as
the GPU backends\
Also holds the video encoder, since writing video needs the same optional libraries as reading it

### midend
Runs one conversion from end to end\
Communicates with backend to tell it what to process\
Depending on the flags set, it provides backend with the data to process\
Also calls the converters to make the jpg png etc\
It handles the saving of the file to the location needed

### backend
Holds all the math and processing that the tool needs\
Where the 'actual' work happens, seperated in functions\
Everything in here works on the whole grid at once rather than one tile at a time, which is what
makes it fast and what lets the same code run on a GPU\
The one definition everything is built on is the *block mean*, documented at the top of the file

### compute
Picks the device the backend's maths runs on, and exposes the handful of array operations it needs\
NumPy on the CPU, CuPy or PyTorch on a GPU\
Nothing in here is imported unless `--gpu` was actually passed, which is what keeps the tool
installable from `requirements.txt` alone

### tools
Has all custom global data and exceptions, as well as some helpful functions

### converters
Houses the code for converting to all output formats\
They all take a `Conversion`: a 2D grid of characters plus an optional matching grid of colours

### ../tests
Checks the vectorised core against the original tile-at-a-time implementation, which is kept
verbatim in `tests/reference.py`. Run with `pytest` from the repository root.

# -=-=-=-=-=-=-=-=-TODOs-=-=-=-=-=-=-=-=-

- [ ] add convertion from link

- [ ] output coloured text straight to the terminal for shells that support it
      (`--print` currently writes the characters only)

- NOTE the tile boundary rounding has to stay in step between `pTileEdges` and whatever the
  CPU path uses, or the two devices produce different pictures. There is a test for this.

- NOTE Pillow's BOX resampling looks like a faster drop-in for the block mean and is not one:
  on some image and grid size combinations it is off by around 11 grayscale levels.
