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


#Bug
#Hack
#fixme
#todo
#note
#[]
#[x ]
#idea

import argparse as ap
import pathlib
from textwrap import dedent
from typing import NoReturn
from PIL import Image

from src import tools, midend

parser: ap.ArgumentParser

def setupParser() -> None:
    """
    Entry point for the tool.
    Sets up the parser and the argument flags needed for this tool to work.
    Also initialises the mid-end and the back-end.
    """
    global parser
    parser = ap.ArgumentParser( # TODO check out prog

        # TODO somehow make these dynamic
        usage = dedent(
'converter.py inputFile [-h] [-a] [-c] \n\
                    [-wi INTEGER | -wc INTEGER] \n\
                    [-hi INTEGER | -hc INTEGER] \n\
                    [-gsc {10,70} (def: 70)] \n\
                    [-op PATH] [-ot {txt, svg, png, jpg, xml} (def: txt)]'
        ),
        
        description = 'Program that converts an input image into an ASCII representation. Usage message formatted for readability.'
  
    )
# usage: converter.py [-h] [-a] [-c] [-wi INTEGER | -wc INTEGER] [-hi INTEGER | -hc INTEGER] [-gsc {10,70}]
#                     [-op PATH | -on STRING] [-t {png,jpg,xml,txt}]
#                     inputFile

    pSetupArguments()

def pSetupArguments() -> None:
    """
    --- Private method! ---\n
    Creates the flags of the tool.
    """

    # TODO add flag for all manual, ignoring other flags except inputfile
    # TODO make auto either be all values or only the missing values

# ========= Main Flags ======== 

    parser.add_argument(    #input file
            'inputFile',
            type        =   pathlib.Path,
            help        =   'The path to the file to be converted'
    )
    parser.add_argument(    # automatic NI
            '-a', '--auto',
            dest        =   'inputAuto',
            required    =   False,
            action      =   'store_true',
            help        =   'Should the program decide the values on its own? NOT IMPLEMENTED'
    )

# ========= Mechanism Flags ======== 

    parser.add_argument(    # colored
            '-c', '--colored',
            dest        =   'inputColored',
            required    =   False,
            action      =   'store_true',
            help        =   'Should the output image be colored instead of greyscale?'
    )

    parser.add_argument(    # how many grayscale TODO
            '-gsc', '--grayscalecount',
            dest        =   'inputGSCount',
            required    =   False,
            type        =   int,
            choices     =   [10,70],
            default     =   70,
            help        =   'How many characters to use for the ASCII representation.'
    )

# ========= Width Flags ======== 

    wgroup = parser.add_mutually_exclusive_group()

    wgroup.add_argument(    # width pixel per tile
            '-wi', '--width',
            dest        =   'inputWidthPixel',
            required    =   False,
            type        =   int,
            help        =   'Tile width in pixels.',
            metavar     =   'INTEGER'
    )
    wgroup.add_argument(    # width total tiles
            '-wc', '--widthcount',
            dest        =   'inputWidthCount',
            required    =   False,
            type        =   int,
            help        =   'Maximum amount of tiles to create on the X axis.',
            metavar     =   'INTEGER'
    )

# ========= Height Flags ======== 

    hgroup = parser.add_mutually_exclusive_group()

    hgroup.add_argument(    # height pixel per tile
            '-hi', '--height',
            dest        =   'inputHeightPixel',
            required    =   False,
            type        =   int,
            help        =   'Tile height in pixels.',
            metavar     =   'INTEGER'
    )
    hgroup.add_argument(    # height total tiles
            '-hc', '--heightcount',
            dest        =   'inputHeightCount',
            required    =   False,
            type        =   int,
            help        =   'Maximum amount of tiles to create on the Y axis.',
            metavar     =   'INTEGER'
    )

# ========= Output Flags ========

    parser.add_argument(    # output path
            '-op', '--outputfilepath',
            dest        =   'inputFilePathOut',
            required    =   False,
            type        =   pathlib.Path,
            #default     =   '\\out',
            help        =   'The full path of the output file.',
            metavar     =   'PATH'
    )
    parser.add_argument(    # output type TODO
            '-ot', '--outputfiletype',
            dest        =   'inputFileTypeOut',
            required    =   False,
            choices     =   tools.ValidTypes.asList(),
            default     =   'txt',
            help        =   'The format of the output file.'
    )

    # TODO change this to be more readable in help message somehow?
    nhelp = "The name of the output file.\
    INPUT uses the same as the input file,\
    RANDOM generates a random readable name,\
    CUSTOM uses the name provided in the output path.\
        If no such path is provided, it uses RANDOM.\
    If path name is provided, program assumes CUSTOM, ignoring the other choices even if they are set."

    parser.add_argument(
            '-on', '--name',
            dest        =   'inputFileNameOut',
            required    =   False,
            choices     =   ['CUSTOM', 'INPUT', 'RANDOM'],
            default     =   'RANDOM',
            help        =   nhelp

    )


def runTool(shouldSave: bool = False): # TODO implement shouldSave, if false return the list instead of saving it (maybe have it do both?)
    args = parser.parse_args()

    try:
        midend.setInputImageFile(args.inputFile)
        midend.setAutomatic(args.inputAuto)
        midend.setColored(args.inputColored)
        midend.setName(args.inputFileNameOut)
    except Exception as e:
        exitWith(e)


    try:
        midend.setGrayscale(args.inputGSCount)
    except tools.Errors.VariableInvalidValueError as e:
        # FIXME: e.value is unknown?
        exitWith(f"Invalid Grayscale size used: {e.value}!")

    imageSize = midend.getInputImageSize()
    print(f"\nInput image dimensions (w x h): {imageSize[0]} x {imageSize[1]} pixels")

    
    # TODO handle for auto
    try:
        midend.HandleWidth(args.inputWidthPixel, args.inputWidthCount) # pass both and let it handle them  
    except tools.Errors.VariableInvalidValueError:
        print("\nInput arguments for width are Invalid!")
        res = pHandleNonexistentTile(imageSize[0], "width") # if there was an error, ask user for value
        midend.setTileWidth(res) # FIXME catch exception
    except tools.Errors.VariableNotInitialisedError:
        res = pHandleNonexistentTile(imageSize[0], "width") # if there was an error, ask user for value
        midend.setTileWidth(res) # FIXME catch exception
        
    try:
        midend.handleHeight(args.inputHeightPixel, args.inputHeightCount) # pass both and let it handle them
    except tools.Errors.VariableInvalidValueError:
        print("\nInput arguments for height are Invalid!")
        res = pHandleNonexistentTile(imageSize[1], "height") # if there was an error, ask user for value
        midend.setTileHeight(res) # FIXME catch exception
    except tools.Errors.VariableNotInitialisedError:
        res = pHandleNonexistentTile(imageSize[1], "height") # if there was an error, ask user for value
        midend.setTileHeight(res) # FIXME catch exception

    tilecountw = int(imageSize[0] / midend.getTileWidth())
    tilecounth = int(imageSize[1] / midend.getTileHeight())

    print(f"Using tile size in pixels (w x h): {midend.getTileWidth()} x {midend.getTileHeight()}")
    print(f"Total tile count \n\tPer axis (w x h): {tilecountw} x {tilecounth}\n\tTotal tiles: {tilecountw*tilecounth}\n")


    midend.handleOutput(args.inputFile, args.inputFilePathOut, args.inputFileTypeOut)

    try:
        midend.execute()
    except tools.Errors.GenericError as e:
        print(e)
        exitWith(e)
        





def pHandleNonexistentTile(img: int, type: str) -> int:
    divs = tools.pGetDivisors(img)
    print(f"\nInput the desired tile {type} size in pixels. Integer divisors of the image {type}:")
    print(divs)
    while True:
        try:
            userin = int(input())
        except Exception:
            exitWith("User issued an exit command during input dialogue.")

        if userin > img or userin < 1:
            print(f"Input a valid integer within the bounds: [1-{img}]!") # TODO add auto option and custom option
        else:
            return userin
        
# FIXME: This takes Exception according to line 208 regards gigagfe (also probably non 0 exit code)
def exitWith(error: Exception | str | None = None) -> NoReturn:
    if error:
        print(f"\nDuring processing, program encountered an error with the message:\n\t{error}\n")
    print("\nTool is exiting...\n")
    exit()
















