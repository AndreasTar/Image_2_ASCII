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

tilePixelsWidth: int = 0
tilePixelsHeight: int = 0

pOutputNameFlag: str




# ================= Main Flags ================ 


# ================= Mechanism Flags ================ 


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

# ================= Output Flags ================

    
# ================= Process ================

def execute(args) -> None:
    """
    Runs the processing of the image. Fetches the parameters set previously.\n
    Should always be run last. If any parameter wasn't set properly, it will crash.\n
    If you believe it crashed when it shouldn't, report it on the github repo by opening a new issue.\n
    Can raise various Exceptions.
    """
    # TODO document the possible Exceptions

    img: Image.Image = args.inputFileImage
    img = img.convert('L')
    resR: list[int] = []
    resG: list[int] = []
    resB: list[int] = []

    if args.pixelated:
        if args.colored:
            img = args.inputFileImage.convert('RGB')
            res = backend.convert2Pixel(img, img.size,\
                                  args.widthCount, args.heightCount)
        else:
            res = backend.convert2Pixel(img, img.size,\
                                  args.widthCount, args.heightCount)
    else:
        grayscaleList = tools.GRAYSCALES.get(args.grayscaleCount)
        res = backend.convert2Ascii(img,\
                                    img.size[0], img.size[1],\
                                    args.widthCount, args.heightCount,\
                                    grayscaleList)
    
    
    if args.colored:
        imgR = args.inputFileImage.getchannel('R')
        imgG = args.inputFileImage.getchannel('G')
        imgB = args.inputFileImage.getchannel('B')

        resR = backend.convert2Ascii(imgR,
                                img.size[0], img.size[1],\
                                args.widthCount, args.heightCount,\
                                onlyColor = True)
        
        resG = backend.convert2Ascii(imgG,
                                img.size[0], img.size[1],\
                                args.widthCount, args.heightCount,\
                                onlyColor = True)
        
        resB = backend.convert2Ascii(imgB,
                                img.size[0], img.size[1],\
                                args.widthCount, args.heightCount,\
                                onlyColor = True)
    if not args.pixelated:
        match args.outputType:
            case tools.ValidTypes.TXT:
                if args.colored:
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
            case tools.ValidTypes.JPG | tools.ValidTypes.PNG:
                res = converters.ConvertToIMG(res, resR, resG, resB, args.colored)
            case tools.ValidTypes.XML:
                if args.colored:
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
                res = converters.ConvertToSVG(res, resR, resG, resB, args.colored)
        


    save(res, args)

def save(data: svg.SVG | Image.Image, args) -> None:
    """
    Saves the data to the output file.
    """
    # TODO  handle and raise errors etc

    pOutputPath = args.outputPath
    pOutputType = args.outputType

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







