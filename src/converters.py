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


# HACK should i use library for this? idk
# also need to control size?
def ConvertToSVG(text: list, red: list | None, green: list | None, blue: list | None):
    
    # adapt for backgroung color maybe?
    elements = [
        svg.Text()
    ]
    
    pass

def ConvertToXML():
    pass