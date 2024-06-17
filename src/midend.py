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


from src import converters, tools, backend

InputImageFile: Image.Image
InputImage_Width: int
InputImage_Height: int

Input_Auto: bool = False
Input_Colored: bool = False
Grayscale_List: str

TilePixels_Width: int = 0
TilePixels_Height: int = 0

_Output_Path: pl.Path

_Output_Ascii: list # TODO change this so it can handle colors for each character


# ================= Main Flags ================ 

def setInputImageFile(inputImagePath: pl.Path):

    global InputImageFile, InputImage_Width, InputImage_Height

    InputImageFile = Image.open(inputImagePath) # FIXME catch exception early
    InputImage_Width, InputImage_Height = InputImageFile.size

def setAutomatic(auto: bool):
    global Input_Auto
    Input_Auto = auto

# ================= Mechanism Flags ================ 

def setColored(color: bool):
    global Input_Colored
    Input_Colored = color

def setGrayscale(gsc: int):
    global Grayscale_List
    if not tools.Grayscales.__contains__(gsc):
        raise tools.ValueInvalidError("gsc", gsc)
    Grayscale_List = tools.Grayscales[gsc]


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
    return getInputImageSize()[0]

def getInputImageHeigth() -> int:
    return getInputImageSize()[1]

# ================= Width Flags ================ 

def setTileWidth(twp: int): # NOTE should this raise an error?

    global TilePixels_Width

    TilePixels_Width = twp

def getTileWidth():
    global TilePixels_Width
    return TilePixels_Width

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

# ================= Height Flags ================

def setTileHeight(thp: int): # NOTE should this raise an error?

    global TilePixels_Height

    TilePixels_Height = thp

def getTileHeight():
    global TilePixels_Height
    return TilePixels_Height

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

# ================= Output Flags ================

def HandleOutput(path: pl.Path, format: str):

    global _Output_Path

    format = "." + format
    
    # get input path
    #   if it exists, create the file there with the name given, whatever that is, and append type at the end
    #   if not, assume current folder and use unique recognisable name and append type at the end

    outFile = ""

    if (not path):
        outFile = tools._getUniqueName()
        #outFile = "temporary_name"
        outFile += format
    else:
        # TODO check if path exists, if it doesnt prompt user to create it or not
        # also make example, cause it works as so:
        #       if test             -> makes \test.txt
        #       if test[/ or \]     -> makes \test.txt -> fixed this with the following if statement
        #       if test[/ or \]name -> makes \test\name.txt
        if path[-1] in {"/", "\\"}:
            path += tools._getUniqueName()
        outFile = pl.Path.cwd().joinpath(path).__str__() + format
        
    
    _Output_Path = pl.Path("", outFile)
    
# ================= Process ================

def Execute():

    img = InputImageFile.convert('L')
    
    res = backend.Convert2Ascii(img,\
                                getInputImageWidth(), getInputImageHeigth(),\
                                getTileWidth(), getTileHeight(),\
                                Grayscale_List)
    Save(res)

def Save(data): 
    # TODO change for other types too like jpg
    # TODO also handle and raise errors etc

    f = open(_Output_Path, 'w')
    for r in data:
        f.write(r + '\n')
    f.close()






