###########################################################################
# Copyright (c) 2024, Andy Pandy                                          #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################

This readme will just explain the general layout of the source code, and the responsibilites of each file,
and also will contain the TODO list for internal operations.

The flow through the tool is one direction only:

    converter.py -> frontend -> midend -> backend -> compute
                        |           \--> converters
                        \--> sources

### converter.py
Tells **frontend** to make the parser and then run\
Also gets the result, error or ascii, and shows it on screen or returns it

### frontend
Holds parser, and prolly not use it much after initialisation\
Makes parser, handles return and error\
Surface checks if flags are ok, and either asks user for input or errors\
Builds a `Config` holding everything the conversion needs, and hands it to the midend\
This is the only file that reads arguments or talks to the user, so everything below it can be driven from code

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
