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

inputImageFile: Image.Image
inputImageWidth: int
inputImageHeight: int

inputAuto: bool = False
inputColored: bool = False
grayscaleList: str

tilePixelsWidth: int = 0
tilePixelsHeight: int = 0

pOutputPath: pl.Path
pOutputType: tools.ValidTypes
pOutputNameFlag: str


# ================= Main Flags ================ 

def setInputImageFile(inputImagePath: pl.Path) -> None:
    """
    Determines if the path given is valid.
    """

    global inputImageFile, inputImageWidth, inputImageHeight

    try:
        inputImageFile = Image.open(inputImagePath)
    except FileNotFoundError:
        raise tools.Errors.GenericError(f"File path was not found -> {inputImagePath}")
    
    inputImageWidth, inputImageHeight = inputImageFile.size

def setAutomatic(auto: bool) -> None:
    global inputAuto
    inputAuto = auto

# ================= Mechanism Flags ================ 

def setColored(color: bool) -> None:
    """
    Setter for the `-c` flag
    """
    global inputColored
    inputColored = color

def setGrayscale(gsc: int) -> None:
    """
    Setter for the grayscale count `-gsc` flag.\n
    Raises VariableInvalidValueError if requested grayscale count isn't implemented.
    """
    global grayscaleList
    if not tools.GRAYSCALES.__contains__(gsc): # NOTE this may look unnecessary cause parser does the checks, but i leave it for api
        raise tools.Errors.VariableInvalidValueError("gsc", gsc)
    grayscaleList = tools.GRAYSCALES[gsc]


def getInputImageSize() -> tuple[int, int]:
    """
    Returns the image dimensions in a tuple(width, height).\n
    Raises VariableNotInitialisedError if called before image was passed.
    """
    global inputImageFile

    if not inputImageFile:
        raise tools.Errors.VariableNotInitialisedError("InputImageFile") # NOTE is this necessary? prolly for future API
    return (inputImageWidth, inputImageHeight)

def getInputImageWidth() -> int:
    """
    Returns the width of the image in pixels.
    """
    return getInputImageSize()[0]

def getInputImageHeight() -> int:
    """
    Returns the height of the image in pixels.
    """
    return getInputImageSize()[1]

# ================= Width Flags ================ 

def setTileWidth(twp: int) -> None: # NOTE should this raise an error?
    """
    Setter for the tile width of the tool in pixels.
    """
    global tilePixelsWidth

    tilePixelsWidth = twp

def getTileWidth() -> int:
    """
    Returns the tile width used in pixels.
    """
    global tilePixelsWidth
    return tilePixelsWidth

def HandleWidth(twp: int, twc: int) -> None:
    """
    Setter for the tile width of the tool in pixels, in either tile count or tile size format.\n
    Raises VariableNotInitialisedError if either value wasn't set.\n
    Raises VariableInvalidValueError if either value was smaller than 1 or above the image size.
    """
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

def setTileHeight(thp: int) -> None: # NOTE should this raise an error?
    """
    Setter for the tile height of the tool in pixels.
    """
    global tilePixelsHeight

    tilePixelsHeight = thp

def getTileHeight() -> int:
    """
    Returns the tile width used in pixels.
    """
    global tilePixelsHeight
    return tilePixelsHeight

def HandleHeight(thp: int, thc: int) -> None:
    """
    Setter for the tile height of the tool in pixels, in either tile count or tile size format.\n
    Raises VariableNotInitialisedError if either value wasn't set.\n
    Raises VariableInvalidValueError if either value was smaller than 1 or above the image size.
    """
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

def setName(nameFlag: str) -> None:
    """
    Setter for the name of the file the tool should save the output as.
    """
    global pOutputNameFlag 
    pOutputNameFlag = nameFlag

def handleOutput(name: pl.Path, path: pl.Path, format: str) -> None:
    """
    Setter for the name of the output file.\n
    If it wasn't given, it uses a randomly generated legible name.
    """

    global pOutputPath, pOutputType

    pOutputType = tools.ValidTypes[format.upper()]

    format = "." + format.lower()

    
    # get input path
    #   if it exists, create the file there with the name given, whatever that is, and append type at the end
    #   if not, assume current folder and use unique recognisable name and append type at the end

    outFile = ""

    if (not path):
        outFile = tools.pGetUniqueName()
        if pOutputNameFlag == 'INPUT':
            outFile = name.name[:-4] # remove format text
        outFile += format
    else:
        # make example, cause it works as so:
        #       if test             -> makes \test.txt
        #       if test[/ or \]     -> makes \test.txt -> fixed this with the following code
        #       if test[/ or \]name -> makes \test\name.txt (iterative, will do as many folders as needed)

        pl.Path.mkdir(path.absolute().parent, parents = True, exist_ok=True)
        outFile = pl.Path.cwd().joinpath(path).__str__() + format
        
    
    pOutputPath = pl.Path("", outFile)
    
# ================= Process ================

def execute() -> None:
    """
    Runs the processing of the image. Fetches the parameters set previously.\n
    Should always be run last. If any parameter wasn't set properly, it will crash.\n
    If you believe it crashed when it shouldn't, report it on the github repo by opening a new issue.\n
    Can raise various Exceptions.
    """
    # TODO document the possible Exceptions

    img = inputImageFile.convert('L')
    resR: list[int] = []
    resG: list[int] = []
    resB: list[int] = []
    
    res = backend.convert2Ascii(img,\
                                getInputImageWidth(), getInputImageHeight(),\
                                getTileWidth(), getTileHeight(),\
                                grayscaleList)
    
    
    if inputColored:
        imgR = inputImageFile.getchannel('R')
        imgG = inputImageFile.getchannel('G')
        imgB = inputImageFile.getchannel('B')

        resR = backend.convert2Ascii(imgR,
                                getInputImageWidth(), getInputImageHeight(),
                                getTileWidth(), getTileHeight(),
                                onlyColor = True)
        
        resG = backend.convert2Ascii(imgG,
                                getInputImageWidth(), getInputImageHeight(),
                                getTileWidth(), getTileHeight(),
                                onlyColor = True)
        
        resB = backend.convert2Ascii(imgB,
                                getInputImageWidth(), getInputImageHeight(),
                                getTileWidth(), getTileHeight(),
                                onlyColor = True)

    match pOutputType:
        case tools.ValidTypes.TXT:
            if inputColored:
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
                            temp += f"{tools.pColorsToHex(resR[r*height +c], resG[r*height +c], resB[r*height +c])[1:].upper()}{res[r][c]} "
                        res[r] = temp

                if inp == 'e':
                    raise tools.Errors.GenericError("Colored flag was set, but output type was .txt! User requested to exit.")     
        case tools.ValidTypes.JPG:
            res = converters.ConvertToIMG(res, resR, resG, resB, inputColored)
        case tools.ValidTypes.PNG:
            res = converters.ConvertToIMG(res, resR, resG, resB, inputColored)
        case tools.ValidTypes.XML:
            if inputColored:
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
                            temp += f"<col>{tools.pColorsToHex(resR[r*height +c], resG[r*height +c], resB[r*height +c])[1:].upper()}</col><char>{res[r][c]}<char> "
                        temp += "</row>\n"
                        res[r] = temp

                if inp == 'e':
                    raise tools.Errors.GenericError("Colored flag was set, but output type was .txt! User requested to exit.")
        case tools.ValidTypes.SVG:
            res = converters.ConvertToSVG(res, resR, resG, resB, inputColored)
        


    save(res)

def save(data: svg.SVG | Image.Image) -> None:
    """
    Saves the data to the output file.
    """
    # TODO  handle and raise errors etc


    f = open(pOutputPath, mode = 'w', encoding = 'utf-8')

    match pOutputType:
        case tools.ValidTypes.TXT:
            for r in data:
                f.write(r + '\n')

        case tools.ValidTypes.JPG:
            data.save(pOutputPath, 'JPEG')
        case tools.ValidTypes.PNG:
            data.save(pOutputPath, 'PNG')
        case tools.ValidTypes.XML:
            for r in data:
                f.write(r + '\n')
        case tools.ValidTypes.SVG:
            f.write(data.as_str())


    f.close()

    print(f"\nSaved file to {pOutputPath}")







