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

# tools -> will have all custom global functions and exceptions

# converters -> will house the code for converting to all output formats


import svg

from src import tools


# HACK should i use library for this? idk
# also need to control size?
def ConvertToSVG(text: list[str], red: list[int] | None, green: list[int] | None, blue: list[int] | None):
    
    # adapt for backgroung color maybe?
    elements = [svg.Style(text = "tspan { font-family: monospace }"),
                svg.Rect(width=3000, height=3000, rx = 9, fill="#111111")] # HACK
    width = len(text[0])
    height = len(text)

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
                        red[r*width + c],
                        green[r*width + c],
                        blue[r*width + c]
                    ),
                    text = tools._formatForSVG(text[r][c])
                )
            )
            x += 12
        x = 0 # HACK fix with this https://gist.github.com/13rac1/7e0b5fb32939685ea44e1a713aac081b
        y += 12
        el.append("\n")
    elements.append(svg.Text(x = 4, y = 4, elements=el))

    return elements   

def ConvertToXML():
    pass