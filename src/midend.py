###########################################################################
# Copyright (c) 2024, Andy Pandy                                          #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################

import pathlib as pl
from PIL import Image
import numpy as np
import svg


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
_Output_Type: tools.ValidTypes
_Output_Name_Flag: str

_Output_Ascii: list # TODO change this so it can handle colors for each character


# ================= Main Flags ================ 

def setInputImageFile(inputImagePath: pl.Path):

    global InputImageFile, InputImage_Width, InputImage_Height

    try:
        InputImageFile = Image.open(inputImagePath)
    except FileNotFoundError:
        raise tools.Errors.GenericError(f"File path was not found -> {inputImagePath}")
    
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
    if not tools.Grayscales.__contains__(gsc): # NOTE this may look unnecessary cause parser does the checks, but i leave it for api
        raise tools.Errors.VariableInvalidValueError("gsc", gsc)
    Grayscale_List = tools.Grayscales[gsc]


def getInputImageSize() -> tuple[int, int]:
    """
    Returns the image dimensions in a tuple(width, height).\n
    Raises VariableNotInitialisedError if called before image was passed.
    """
    global InputImageFile

    if not InputImageFile:
        raise tools.Errors.VariableNotInitialisedError("InputImageFile") # NOTE is this necessary? prolly for future API
    return (InputImage_Width, InputImage_Height)

def getInputImageWidth() -> int:
    return getInputImageSize()[0]

def getInputImageHeight() -> int:
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
        raise tools.Errors.VariableNotInitialisedError("twp")
    
    if twp:
        if (twp < 1 or twp > getInputImageWidth()):
            raise tools.Errors.VariableInvalidValueError("twp", twp, "Invalid input tile width!")
        setTileWidth(twp)

    else:
        if (twc < 1 or twc > getInputImageWidth()):
            raise tools.Errors.VariableInvalidValueError("twc", twc, "Invalid input tile width!")
        
        temp = int(np.ceil( getInputImageWidth() / twc ))
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
        raise tools.Errors.VariableNotInitialisedError("thp")
    
    if thp:
        if (thp < 1 or thp > getInputImageHeight()):
            raise tools.Errors.VariableInvalidValueError("thp", thp, "Invalid input tile height!")
        setTileHeight(thp)

    else:
        if (thc < 1 or thc > getInputImageHeight()):
            raise tools.Errors.VariableInvalidValueError("thc", thc, "Invalid input tile height!")
        
        temp = int(np.ceil( getInputImageHeight() / thc ))
        setTileHeight(temp)

# ================= Output Flags ================

def setName(nameFlag: str):
    global _Output_Name_Flag 
    _Output_Name_Flag = nameFlag

def HandleOutput(name: pl.Path, path: pl.Path, format: str):

    global _Output_Path, _Output_Type

    _Output_Type = tools.ValidTypes[format.upper()]

    format = "." + format.lower()

    
    # get input path
    #   if it exists, create the file there with the name given, whatever that is, and append type at the end
    #   if not, assume current folder and use unique recognisable name and append type at the end

    outFile = ""

    if (not path):
        outFile = tools._getUniqueName()
        if _Output_Name_Flag == 'INPUT':
            outFile = name.name[:-4] # remove format text
        outFile += format
    else:
        # make example, cause it works as so:
        #       if test             -> makes \test.txt
        #       if test[/ or \]     -> makes \test.txt -> fixed this with the following code
        #       if test[/ or \]name -> makes \test\name.txt (iterative, will do as many folders as needed)

        pl.Path.mkdir(path.absolute().parent, parents = True, exist_ok=True)
        outFile = pl.Path.cwd().joinpath(path).__str__() + format
        
    
    _Output_Path = pl.Path("", outFile)
    
# ================= Process ================

def Execute():

    img = InputImageFile.convert('L')
    resR: list[int] = []
    resG: list[int] = []
    resB: list[int] = []
    
    res = backend.Convert2Ascii(img,\
                                getInputImageWidth(), getInputImageHeight(),\
                                getTileWidth(), getTileHeight(),\
                                Grayscale_List)
    
    
    if Input_Colored:
        imgR = InputImageFile.getchannel('R')
        imgG = InputImageFile.getchannel('G')
        imgB = InputImageFile.getchannel('B')

        resR = backend.Convert2Ascii(imgR,
                                getInputImageWidth(), getInputImageHeight(),
                                getTileWidth(), getTileHeight(),
                                onlyColor = True)
        
        resG = backend.Convert2Ascii(imgG,
                                getInputImageWidth(), getInputImageHeight(),
                                getTileWidth(), getTileHeight(),
                                onlyColor = True)
        
        resB = backend.Convert2Ascii(imgB,
                                getInputImageWidth(), getInputImageHeight(),
                                getTileWidth(), getTileHeight(),
                                onlyColor = True)

    match _Output_Type:
        case tools.ValidTypes.TXT:
            if Input_Colored:
                print("\nInput flag { -c : Colored } was set, but output type is .txt! Choose one of the following:")
                print("\tOutput only the ASCII characters -> t")
                print("\tOutput colors and text in per-pixel format : [RRGGBBc RRGGBBc ...] -> c")
                print("\tExit without proceeding -> e")
                inp: str
                while True:
                    inp = input("Leave empty for default (e) : ").lower()
                    if not inp:
                        inp = 'e'
                        break
                    if inp in 'tce':
                        break
                
                if inp == 't':
                    print("Outputting only the ASCII characters.")
                    pass # do nothing with the colors

                if inp == 'c':
                    print("Converting output to per-pixel format : [RRGGBBc RRGGBBc RRGGBBc ...]")
                    height = len(res)
                    width = len(res[0])

                    for r in range(height):
                        temp = ""
                        for c in range(width):
                            temp += f"{tools._colorsToHex(resR[r*height +c], resG[r*height +c], resB[r*height +c])[1:].upper()}{res[r][c]} "
                        res[r] = temp

                if inp == 'e':
                    raise tools.Errors.GenericError("Colored flag was set, but output type was .txt! User requested to exit.")
                
        case tools.ValidTypes.JPG:
            res = converters.ConvertToPNG(res, resR, resG, resB, Input_Colored)
        case tools.ValidTypes.PNG:
            res = converters.ConvertToPNG(res, resR, resG, resB, Input_Colored)
        case tools.ValidTypes.XML:
            if Input_Colored:
                print("\nInput flag { -c : Colored } was set, but output type is .xml! Choose one of the following:")
                print("\tOutput only the ASCII characters in format : [<char>c</char> ...] -> t")
                print("\tOutput colors and text in per-character format : [<col>RRGGBB</col><char>c</char> ...] -> c")
                print("\tExit without proceeding -> e")
                inp: str
                while True:
                    inp = input("Leave empty for default (e) : ").lower()
                    if not inp:
                        inp = 'e'
                        break
                    if inp in 'tce':
                        break
                
                if inp == 't':
                    print("Outputting only the ASCII characters in format : [<char>c</char> ...]")
                    height = len(res)
                    width = len(res[0])

                    for r in range(height):
                        temp = "<row>\n\t"
                        for c in range(width):
                            temp += f"<char>{res[r][c]}<char> "
                        temp += "</row>\n"
                        res[r] = temp

                if inp == 'c':
                    print("Converting output to per-character format : [<col>RRGGBB</col><char>c</char> ...]")
                    height = len(res)
                    width = len(res[0])

                    for r in range(height):
                        temp = "<row>\n\t"
                        for c in range(width):
                            temp += f"<col>{tools._colorsToHex(resR[r*height +c], resG[r*height +c], resB[r*height +c])[1:].upper()}</col><char>{res[r][c]}<char> "
                        temp += "</row>\n"
                        res[r] = temp

                if inp == 'e':
                    raise tools.Errors.GenericError("Colored flag was set, but output type was .txt! User requested to exit.")
        case tools.ValidTypes.SVG:
            res = converters.ConvertToSVG(res, resR, resG, resB, Input_Colored)
        


    Save(res)

def Save(data: svg.SVG | Image.Image): 
    # TODO  handle and raise errors etc


    f = open(_Output_Path, mode = 'w', encoding = 'utf-8')

    match _Output_Type:
        case tools.ValidTypes.TXT:
            for r in data:
                f.write(r + '\n')

        case tools.ValidTypes.JPG:
            data.save(_Output_Path, 'JPEG')
        case tools.ValidTypes.PNG:
            data.save(_Output_Path, 'PNG')
        case tools.ValidTypes.XML:
            for r in data:
                f.write(r + '\n')
        case tools.ValidTypes.SVG:
            f.write(data.as_str())


    f.close()

    print(f"\nSaved file to {_Output_Path}")







