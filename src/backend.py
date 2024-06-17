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

from PIL import Image # type: ignore
import numpy as np # type: ignore

def Convert2Ascii(image: Image.Image,\
                  imgHeight: int, imgWidth: int,\
                  tileHeight: int, tileWidth: int,\
                  charList: list, onlyColor: bool = False):

    asciiImage = []                     # each row is a string

    rowIndex = int(imgHeight / tileHeight)
    colIndex = int(imgWidth / tileWidth)

    charSize = len(charList) -1

    for row in range(rowIndex):
        ytop = row * tileHeight             # top bounds of tile
        ybot = (row+1) * tileHeight         # bot bounds of tile

        if row == rowIndex-1:               # if its the last row, fill to end
            ybot = imgHeight
        asciiImage.append('')

        for col in range(colIndex):
            xleft = col * tileWidth         # left bounds of tile
            xright = (col+1) * tileWidth    # right bounds of tile
            
            if col == colIndex-1:
                xright = imgWidth           # if its last column, fill to end
            
            tile = image.crop((xleft, ytop, xright, ybot))

            val = int(_getAverage(tile))

            if not onlyColor:               # if we want the ascii character instead of just color value
                val = charList[int((val *  charSize) / 255)]
            
            asciiImage[row] += val 
    pass

def _getAverage(tile: Image.Image):
    npImg = np.array(tile)
    tw, th = npImg.shape

    return np.average(npImg.reshape(tw*th))

