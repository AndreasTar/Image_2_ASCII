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
from PIL import Image # type: ignore
import numpy as np # type: ignore

import tools
import converters, backend

InputImageFile: Image.Image
InputImage_Width: int
InputImage_Height: int

Input_Auto: bool = False

TilePixels_Width: int = 0
TilePixels_Height: int = 0


_Output_Ascii: list # TODO change this so it can handle colors for each character

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
        raise tools.ValueNotInitialisedError("InputImageFile") # NOTE is this necessary? prolly for future API
    return (InputImage_Width, InputImage_Height)

def getInputImageWidth() -> int:
    return getInputImageSize[0]

def getInputImageHeigth() -> int:
    return getInputImageSize[1]

def setTileWidth(twp: int): # NOTE should this raise an error?

    global TilePixels_Width

    TilePixels_Width = twp

def HandleWidth(twp: int, twc: int):
    if not (twp or twc):
        raise tools.ValueNotInitialisedError("twp")
    if twp:
        if (twp < 1 or twp > getInputImageWidth):
            print("Invalid input tile width!")
            raise tools.ValueInvalidError("twp", twp)
        setTileWidth(twp)
    else:
        if (twc < 1 or twc > getInputImageWidth):
            print("Invalid input tile width!")
            raise tools.ValueInvalidError("twc", twc)
        temp = int(np.ceil( getInputImageWidth / twc ))
        setTileWidth(temp)

def HandleHeight(thp: int, thc: int):
    if not (thp or thc):
        raise tools.ValueNotInitialisedError("thp")
    if thp:
        if (thp < 1 or thp > getInputImageWidth):
            print("Invalid input tile height!")
            raise tools.ValueInvalidError("thp", thp)
        setTileWidth(thp)
    else:
        if (thc < 1 or thc > getInputImageWidth):
            print("Invalid input tile height!")
            raise tools.ValueInvalidError("thc", thc)
        temp = int(np.ceil( getInputImageWidth / thc ))
        setTileWidth(temp)


def setTileHeight(thp: int): # NOTE should this raise an error?

    global TilePixels_Height

    TilePixels_Height = thp



def setAutomatic(auto: bool):
    global Input_Auto
    Input_Auto = auto

