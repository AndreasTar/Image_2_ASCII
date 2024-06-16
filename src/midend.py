###########################################################################
# Copyright (c) 2024, Andy Pandy                                          #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################


# main -> tells frontend to make parser and then run
#         also gets result, error or ascii, and shows it on screen or returns it

# frontend -> will hold parser, and prolly not use it much after initialisation
#             makes parser, handles return and error
#             surface checks if flags are ok, and either asks or errors
#             calls stuff from midend depending on flags

# midend -> will hold the ascii array
#           communicates with backend to tell it what to process
#           depending on the function called, it will provide backend with data to process
#           will also call the converters to make the jpg png etc
#           it will handle the saving of the file to the location needed

# backend -> will hold all the math and processing that the tool needs
#            where the 'actual' work happens, seperated in functions

import pathlib as pl
from PIL import Image

import tools
import converters, backend

InputImageFile: Image.Image
InputImage_Width: int
InputImage_Height: int

TileWidthPixels: int = 0
TileHeightPixels: int = 0

def setInputImageFile(inputImagePath: pl.Path):

    global InputImageFile, InputImage_Width, InputImage_Height

    InputImageFile = Image.open(inputImagePath) # FIXME catch exception early
    InputImage_Width, InputImage_Height = InputImageFile.size

def getInputImageSize() -> tuple[int, int]:
    """
    Returns the image dimensions in a tuple(width, height).\n
    Raises ValueNotInitialisedError if called before image was passed.
    """
    global InputImageFile

    if not InputImageFile:
        raise tools.ValueNotInitialisedError("InputImageFile")
    return (InputImage_Width, InputImage_Height)

def setTileWidth(twp: int): # NOTE should this raise an error?

    global TileWidthPixels

    TileWidthPixels = twp

def setTileHeight(thp: int): # NOTE should this raise an error?

    global TileHeightPixels

    TileHeightPixels = thp

