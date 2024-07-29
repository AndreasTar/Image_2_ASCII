###########################################################################
# Copyright (c) 2024, Andy Pandy                                          #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################

import svg
from PIL import Image, ImageDraw

from src import tools

# this may be useful https://gist.github.com/TruncatedDinoSour/83f324cb156ca8cd58284d436a0d9f75

# does it need to control size via params?
def ConvertToSVG(text: list[str], red: list[int] | None, green: list[int] | None, blue: list[int] | None, colored: bool) -> svg.SVG:
    
    width = len(text[0])
    height = len(text)

    elements = [svg.Style(text = "tspan { font-family: monospace }"),
                svg.Rect(width=width*12, height=height*12 + 3, rx = 9, fill= "#111111" if colored else "#EEEEEE")]


    el = []
    y = 14
    x = 0

    for r in range(height):
        for c in range(width):
            el.append(
                svg.TSpan(
                    x = x,
                    y = y,
                    fill = tools._colorsToHex(
                        red[r*width + c] if not (len(red) == 0 or not red) else 0,
                        green[r*width + c] if not (len(green) == 0 or not green) else 0,
                        blue[r*width + c] if not (len(blue) == 0 or not blue) else 0
                    ),
                    text = tools._formatForSVG(text[r][c])
                )
            )
            x += 12
        # HACK fix with this https://gist.github.com/13rac1/7e0b5fb32939685ea44e1a713aac081b 
        # or this https://stackoverflow.com/questions/64660531/is-there-a-precise-way-to-measure-text-size-in-a-specific-font-in-python-3-7
        x = 0
        y += 12
        el.append("\n")
    elements.append(svg.Text(x = 4, y = 4, elements=el))

    file = svg.SVG(
        width = width*12,
        height = height*12 + 3,
        elements = elements,
    )

    return file   

def ConvertToIMG(text: list[str], red: list[int] | None, green: list[int] | None, blue: list[int] | None, colored: bool) -> Image.Image:

    width = len(text[0])
    height = len(text)

    img = Image.new('RGB', (width*12, height*12+3), (17,17,17) if colored else (238,238,238))

    d = ImageDraw.Draw(img)
    y = 0
    x = 0

    for r in range(height):
        for c in range(width):

            d.text(
                (x,y),
                text[r][c],
                tools._colorsToHex(
                    red[r*width + c] if not (len(red) == 0 or not red) else 0,
                    green[r*width + c] if not (len(green) == 0 or not green) else 0,
                    blue[r*width + c] if not (len(blue) == 0 or not blue) else 0
                )
            )
            x += 12
        x = 0
        y += 12
    return img