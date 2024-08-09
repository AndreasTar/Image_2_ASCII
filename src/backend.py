###########################################################################
# Copyright (c) 2024, Andy Pandy                                          #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################

from typing import Any
from PIL import Image
import numpy as np

def convert2Ascii(image: Image.Image,\
                  imgWidth: int, imgHeight: int,\
                  tileWidth: int, tileHeight: int,\
                  charList: list[str] | str | None = None, onlyColor: bool = False) -> list:

    if (charList is None and not onlyColor):
        # TODO: Return exception
        assert False, "Charlist is none and not only color" 
    
    asciiImage = []                     # each row is a string

    rowIndex = int(imgHeight / tileHeight)
    colIndex = int(imgWidth / tileWidth)
    # FIXME: Charsize may be unbound due to it only being bound inside this check 
    if charList:
        charSize = len(charList) -1

    for row in range(rowIndex):
        ytop = row * tileHeight             # top bounds of tile
        ybot = (row+1) * tileHeight         # bot bounds of tile

        if row == rowIndex-1:               # if its the last row, fill to end
            ybot = imgHeight

        if not onlyColor:
            asciiImage.append('')

        for col in range(colIndex):
            xleft = col * tileWidth         # left bounds of tile
            xright = (col+1) * tileWidth    # right bounds of tile
            
            if col == colIndex-1:
                xright = imgWidth           # if its last column, fill to end
            
            tile = image.crop((xleft, ytop, xright, ybot))

            val = int(pGetAverage(tile))

            if not onlyColor:               # if we want the ascii character instead of just color value
                val = charList[int((val *  charSize) / 255)]
                asciiImage[row] += val
            else:
                asciiImage.append(val)

    return asciiImage

# TODO: type hint return type
def pGetAverage(tile: Image.Image) -> np.floating[Any]:
    npImg = np.array(tile)
    tw, th = npImg.shape

    return np.average(npImg.reshape(tw*th))

