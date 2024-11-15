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
#             it will handle the saving of the file to the location needed

# midend -> will hold the ascii array
#           communicates with backend to tell it what to process
#           depending on the function called, it will provide backend with data to process
#           will also call the converters to make the jpg png etc

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
import pathlib as pl
from textwrap import dedent
from typing import NoReturn
from PIL import Image

from src import tools, midend

parser: ap.ArgumentParser

class InputArguments():
    inputFileImage: Image.Image
    automatic: bool = False
    colored: bool = False
    pixelated: bool = False
    grayscaleCount: int = 70
    widthCount: int = 0
    heightCount: int = 0
    outputPath: pl.Path
    outputType: list[str] = tools.ValidTypes.asList()
    outputName: str = 'RANDOM'

def setupParser() -> None:
    """
    Entry point for the tool.
    Sets up the parser and the argument flags needed for this tool to work.\n
    Also initialises the mid-end and the back-end.
    """
    global parser
    parser = ap.ArgumentParser( # TODO check out prog

        # TODO somehow make these dynamic
        usage = dedent(
'converter.py inputFile [-h] [-a] [-c] [-pix] \n\
                    [-wi INTEGER | -wc INTEGER] \n\
                    [-hi INTEGER | -hc INTEGER] \n\
                    [-gsc {10,70} (def: 70)] \n\
                    [-op PATH] [-ot {txt, svg, png, jpg, xml} (def: txt)]'
        ),
        
        description = 'Program that converts an input image into an ASCII representation. Usage message formatted for readability.'
  
    )
# usage: converter.py [-h] [-a] [-c] [-pix] [-wi INTEGER | -wc INTEGER] [-hi INTEGER | -hc INTEGER] [-gsc {10,70}]
#                     [-op PATH | -on STRING] [-t {png,jpg,xml,txt,svg}]
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
            type        =   pl.Path,
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

    tgroup = parser.add_mutually_exclusive_group()

    tgroup.add_argument(    # how many grayscale TODO
            '-gsc', '--grayscalecount',
            dest        =   'inputGSCount',
            required    =   False,
            type        =   int,
            choices     =   [10,70],
            default     =   70,
            help        =   'How many characters to use for the ASCII representation.'
    )

    tgroup.add_argument(    # how many grayscale TODO
            '-pix', '--pixelated',
            dest        =   'inputPixelated',
            required    =   False,
            action      =   'store_true',
            help        =   'Convert the image into pixelart instead of ASCII. Only image output types are allowed. (SVG and TXT will error)'
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
            type        =   pl.Path,
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
    '''
    Begins the processing of the image with the given flags.\n
    If some flags are not set, it will request them from the user.
    If that cant be done, it will exit with an error message.
    '''
    args = parser.parse_args()

    inputArguments = InputArguments

    try:
        inputArguments.inputFileImage = Image.open(args.inputFile)
    except FileNotFoundError:
        exitWith(f"File path was not found -> {args.inputFile}")
        #raise tools.Errors.GenericError(f"File path was not found -> {args.inputFile}")
    
    inputArguments.automatic = args.inputAuto
    inputArguments.colored = args.inputColored
    inputArguments.pixelated = args.inputPixelated

    if not inputArguments.pixelated:
        if not tools.GRAYSCALES.__contains__(args.inputGSCount):
            exitWith(f"Invalid Grayscale size used: {e.varValue}!") # IDEA maybe fallback?
        inputArguments.grayscaleCount = args.inputGSCount

    inputArguments.widthCount = HandleWidth(args.inputWidthPixel, args.inputWidthCount, inputArguments.inputFileImage.size[0])
    inputArguments.heightCount = HandleHeight(args.inputHeightPixel, args.inputHeightCount, inputArguments.inputFileImage.size[1])

    inputArguments.outputName = args.inputFileNameOut
    inputArguments.outputPath, inputArguments.outputType = HandleOutput(args.inputFile, args.inputFilePathOut, args.inputFileTypeOut, args.inputFileNameOut) 

    #check pixelated
    if inputArguments.pixelated:
        if not (inputArguments.outputType.name in tools.ValidTypes.getImageTypes()):
            exitWith("Can't do pixelart with non-image type output!")

    print(f"\nInput image dimensions (w x h): {inputArguments.inputFileImage.size[0]} x {inputArguments.inputFileImage.size[1]} pixels")

    tilesizew = int(inputArguments.inputFileImage.size[0] / inputArguments.widthCount)
    tilesizeh = int(inputArguments.inputFileImage.size[1] / inputArguments.heightCount)

    print(f"Using tile size in pixels (w x h): {tilesizew} x {tilesizeh}")
    print(f"Total tile count \n\tPer axis (w x h): {inputArguments.widthCount} x {inputArguments.heightCount}\n\tTotal tiles: {inputArguments.widthCount * inputArguments.heightCount}\n")


    try:
        midend.execute(inputArguments)
    except tools.Errors.GenericError as e:
        print(e)
        exitWith(e)
        

def HandleWidth(twp: int, twc: int, imgWidth: int):
    if not (twp or twc):
        twp = pHandleNonexistentTile(imgWidth, "width")
        return twp
    
    if twp:
        if (twp < 1 or twp > imgWidth):
            print("\nInput arguments for width are Invalid!")
            twp = pHandleNonexistentTile(imgWidth, "width")

        from numpy import ceil
        temp = int(ceil( imgWidth / twp ))
        return temp

    else:
        if (twc < 1 or twc > imgWidth):
            print("\nInput arguments for width are Invalid!")
            twc = pHandleNonexistentTile(imgWidth, "width")
        
        return twc

def HandleHeight(thp: int, thc: int, imgHeight: int) -> None:
    if not (thp or thc):
        print("\nInput arguments for height not found! Prompting user...")
        thp = pHandleNonexistentTile(imgHeight, "height")
    
    if thp:
        if (thp < 1 or thp > imgHeight):
            print("\nInput arguments for height are Invalid!")
            thp = pHandleNonexistentTile(imgHeight, "height")

        from numpy import ceil
        temp = int(ceil( imgHeight / thp ))
        return temp

    else:
        if (thc < 1 or thc > imgHeight):
            print("\nInput arguments for height are Invalid!")
            thc = pHandleNonexistentTile(imgHeight, "height")
        
        return thc
    
def HandleOutput(name: pl.Path, path: pl.Path, format: str, nameOut: str):

    # get input path
    #   if it exists, create the file there with the name given, whatever that is, and append type at the end
    #   if not, assume current folder and use unique recognisable name and append type at the end

    format = "." + format.lower()
    outFile = ""

    if (not path):
        outFile = tools.pGetUniqueName()
        if nameOut == 'INPUT':
            outFile = name.name[:-4] # remove format text
        outFile += format
    else:
        # make example, cause it works as so:
        #       if test             -> makes \test.txt
        #       if test[/ or \]     -> makes \test.txt -> fixed this with the following code
        #       if test[/ or \]name -> makes \test\name.txt (iterative, will do as many folders as needed)

        pl.Path.mkdir(path.absolute().parent, parents = True, exist_ok=True)
        outFile = pl.Path.cwd().joinpath(path).__str__() + format
        
    
    return pl.Path("", outFile), tools.ValidTypes[format[-3:].upper()]


def pHandleNonexistentTile(img: int, type: str) -> int:
    """
    --- Private method! ---\n
    If the tile size flags were not set upon execution, this will prompt the user to specify them.
    """

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
        


def exitWith(error: Exception | str | None = None) -> NoReturn:
    code = 0
    if error:
        print(f"\n{"-="*18} ERROR {"=-"*18}=\n\nDuring processing, program encountered an error with the message:\n\t{error}\n\n{"-="*40}\n")
        # Non zero exit code indicates something went wrong
        code = 1
    print("\nTool is exiting...\n")
    exit(code)
















