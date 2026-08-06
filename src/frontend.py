###########################################################################
# Copyright (c) 2024-2026, Andreas Tarasidis (Andy Pandy)                 #
#                                                                         #
# Original repo: https://github.com/AndreasTar/Image_2_ASCII              #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################

"""
The command line surface.

Owns the parser, checks the flags make sense, asks the user for anything missing that
cannot be worked out, and hands a finished `Config` to the midend. Nothing downstream
touches argparse or prompts the user, so the rest of the tool can be driven from code.
"""

import argparse as ap
import pathlib as pl
import shutil
from math import ceil
from textwrap import dedent
from typing import NoReturn

from PIL import Image, UnidentifiedImageError

from src import backend, compute, config, midend, sources, tools
# Re-exported rather than defined here, so that the GUI can describe a conversion without
# importing the command line. Kept at module level because `frontend.Config` is how the
# rest of the tool has always referred to it.
from src.config import DEFAULT_EDGE_SENSITIVITY, Config

parser: ap.ArgumentParser

# How many divisors to list before truncating, so a prompt for a large image stays readable.
MAX_LISTED_DIVISORS = 40

NAME_CHOICES = ('CUSTOM', 'INPUT', 'RANDOM')


def setupParser() -> None:
    """
    Entry point for the tool.
    Sets up the parser and the argument flags needed for this tool to work.
    """
    global parser
    parser = ap.ArgumentParser(
        prog = 'converter.py',

        usage = dedent(
'converter.py inputFile [-h] [-v] [-a] [-c] [-pix] [-i] [-e] [-p] [-d] [--alpha] [--frames] \n\
                       [-wi INTEGER | -wc INTEGER] \n\
                       [-hi INTEGER | -hc INTEGER] \n\
                       [-gsc {10,70} (def: 70) | -gs STRING | -cs CHARSET] \n\
                       [-th 0-255] [-tb 0-255 0-255] [-et 0-100 (def: 90)] [-ca FLOAT (def: 0.5)] \n\
                       [-g [auto|cupy|torch]] \n\
                       [--maxframes INTEGER] [--framestep INTEGER] [--fps FLOAT] \n\
                       [-op PATH] [-ot {txt, svg, png, jpg, xml, gif, mp4} (def: txt)] \n\
                       [-on {CUSTOM, INPUT, RANDOM} (def: RANDOM)] \n'
        ),

        description = 'Program that converts an input image into an ASCII representation. '
                      'Usage message formatted for readability.'
    )

    pSetupArguments()


def pSetupArguments() -> None:
    """
    --- Private method! ---\n
    Creates the flags of the tool.
    """

# ========= Main Flags ========

    parser.add_argument(    # input file
            'inputFile',
            type        =   pl.Path,
            help        =   'The path to the file to be converted'
    )
    parser.add_argument(    # automatic
            '-a', '--auto',
            dest        =   'inputAuto',
            required    =   False,
            action      =   'store_true',
            help        =   'Work out any tile counts that were not given, from the image aspect ratio '
                            'and the terminal size, instead of asking for them.'
    )
    parser.add_argument(    # version of the app
            '-v', '--version',
            action      =   'version',
            help        =   'The version of the app',
            version     =  f'Version: {tools.APP_VERSION}',
    )

# ========= Mechanism Flags ========

    parser.add_argument(    # colored
            '-c', '--colored',
            dest        =   'inputColored',
            required    =   False,
            action      =   'store_true',
            help        =   'Should the output image be colored instead of greyscale?'
    )
    parser.add_argument(    # invert
            '-i', '--invert',
            dest        =   'inputInvert',
            required    =   False,
            action      =   'store_true',
            help        =   'Put the dense characters on the bright areas instead of the dark ones.'
    )
    parser.add_argument(    # threshold
            '-th', '--threshold',
            dest        =   'inputThreshold',
            required    =   False,
            type        =   pIntInRange(0, 255),
            help        =   'Collapse the image to two tones at this brightness cutoff (0-255).',
            metavar     =   'INTEGER'
    )
    parser.add_argument(    # band threshold
            '-tb', '--thresholdband',
            dest        =   'inputBand',
            required    =   False,
            nargs       =   2,
            type        =   pIntInRange(0, 255),
            help        =   'Keep only the brightnesses between these two values (0-255), erasing '
                            'everything outside them. What is kept looks exactly as it would '
                            'without this flag, unlike -th which rewrites every value. Erased '
                            'cells become blank characters, or transparent blocks with -pix.',
            metavar     =   'INTEGER'
    )
    parser.add_argument(    # edge detection
            '-e', '--edges',
            dest        =   'inputEdges',
            required    =   False,
            action      =   'store_true',
            help        =   'Detect edges and draw them with directional characters ( | / - \\ ).'
    )
    parser.add_argument(    # edge sensitivity
            '-et', '--edgethreshold',
            dest        =   'inputEdgeSensitivity',
            required    =   False,
            type        =   pIntInRange(0, 100),
            default     =   DEFAULT_EDGE_SENSITIVITY,
            help        =   f'How much of the image becomes edges, as a percentile of gradient strength '
                            f'(0-100, default {DEFAULT_EDGE_SENSITIVITY} which keeps the strongest 10%%). '
                            f'Lower finds more edges.',
            metavar     =   'INTEGER'
    )
    parser.add_argument(    # character aspect ratio
            '-ca', '--charaspect',
            dest        =   'inputCharAspect',
            required    =   False,
            type        =   pFloatAbove(0.0),
            default     =   tools.DEFAULT_CHAR_ASPECT,
            help        =   f'Width of a character cell divided by its height, used to stop the output '
                            f'coming out stretched (default {tools.DEFAULT_CHAR_ASPECT}).',
            metavar     =   'FLOAT'
    )
    parser.add_argument(    # alpha
            '--alpha',
            dest        =   'inputAlpha',
            required    =   False,
            action      =   'store_true',
            help        =   'Flatten transparent areas onto black instead of ignoring the alpha channel.'
    )
    parser.add_argument(    # gpu
            '-g', '--gpu',
            dest        =   'inputGpu',
            required    =   False,
            nargs       =   '?',
            const       =   'auto',
            default     =   None,
            choices     =   compute.BACKEND_CHOICES,
            help        =   'Run the maths on the GPU. Needs CuPy or a GPU build of PyTorch installed; '
                            'neither ships with the tool, and without one this falls back to the CPU.'
    )

    tgroup = parser.add_mutually_exclusive_group()

    tgroup.add_argument(    # how many grayscale
            '-gsc', '--grayscalecount',
            dest        =   'inputGSCount',
            required    =   False,
            type        =   int,
            choices     =   sorted(tools.GRAYSCALES),
            default     =   70,
            help        =   'How many characters to use for the ASCII representation.'
    )
    tgroup.add_argument(    # custom ramp
            '-gs', '--grayscale',
            dest        =   'inputGrayscale',
            required    =   False,
            type        =   str,
            help        =   'A custom character ramp to use, ordered densest first, e.g. "@#+-. ".',
            metavar     =   'STRING'
    )
    tgroup.add_argument(    # named character set
            '-cs', '--charset',
            dest        =   'inputCharSet',
            required    =   False,
            choices     =   sorted(tools.CHARSETS),
            help        =   'A built-in character set. ' +
                            '; '.join(f"{name} = {charSet.description}"
                                      for name, charSet in sorted(tools.CHARSETS.items())) + '.'
    )
    tgroup.add_argument(    # pixelart
            '-pix', '--pixelated',
            dest        =   'inputPixelated',
            required    =   False,
            action      =   'store_true',
            help        =   'Convert the image into pixelart instead of ASCII. '
                            'Only image output types are allowed. (SVG and TXT will error)'
    )

    parser.add_argument(    # dithering
            '-d', '--dither',
            dest        =   'inputDither',
            required    =   False,
            action      =   'store_true',
            help        =   'Use ordered dithering for the dot based character sets (braille, quadrants, '
                            'halfblocks) instead of one flat cutoff. Worth it at high tile counts, noisy at low ones.'
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
            help        =   'Exact amount of tiles to create on the X axis.',
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
            help        =   'Exact amount of tiles to create on the Y axis.',
            metavar     =   'INTEGER'
    )

# ========= Output Flags ========

    parser.add_argument(    # output path
            '-op', '--outputfilepath',
            dest        =   'inputFilePathOut',
            required    =   False,
            type        =   pl.Path,
            help        =   'The full path of the output file.',
            metavar     =   'PATH'
    )
    parser.add_argument(    # output type
            '-ot', '--outputfiletype',
            dest        =   'inputFileTypeOut',
            required    =   False,
            choices     =   tools.ValidTypes.asList(),
            default     =   'txt',
            help        =   'The format of the output file.'
    )
    parser.add_argument(    # print to screen
            '-p', '--print',
            dest        =   'inputPrint',
            required    =   False,
            action      =   'store_true',
            help        =   'Write the result to the screen. Nothing is saved unless -op is also given. '
                            'Not available for the image output types. An animation plays in place, '
                            'and with -c the output is coloured.'
    )
    parser.add_argument(    # numbered frames
            '--frames',
            dest        =   'inputFrames',
            required    =   False,
            action      =   'store_true',
            help        =   'Write every frame as its own numbered file, in a subfolder created next to '
                            'the output path. Needed to convert an animation to a single-file format.'
    )

# ========= Animation Flags ========

    parser.add_argument(    # cap on frames
            '--maxframes',
            dest        =   'inputMaxFrames',
            required    =   False,
            type        =   pIntInRange(1, 1_000_000),
            help        =   'Stop after this many frames. Useful for trying settings on a long clip.',
            metavar     =   'INTEGER'
    )
    parser.add_argument(    # frame stride
            '--framestep',
            dest        =   'inputFrameStep',
            required    =   False,
            type        =   pIntInRange(1, 1000),
            default     =   1,
            help        =   'Keep only every Nth frame. Playback speed is preserved, the result is choppier.',
            metavar     =   'INTEGER'
    )
    parser.add_argument(    # output frame rate
            '--fps',
            dest        =   'inputFps',
            required    =   False,
            type        =   pFloatAbove(0.0),
            help        =   'Override the output frame rate. Defaults to the frame rate of the input.',
            metavar     =   'FLOAT'
    )

    nhelp = "The name of the output file. \
    INPUT uses the same as the input file, \
    RANDOM generates a random readable name, \
    CUSTOM uses the name provided in the output path. \
        If no such path is provided, it uses RANDOM. \
    If path name is provided, program assumes CUSTOM, ignoring the other choices even if they are set."

    parser.add_argument(
            '-on', '--name',
            dest        =   'inputFileNameOut',
            required    =   False,
            choices     =   NAME_CHOICES,
            default     =   'RANDOM',
            help        =   nhelp
    )


def runTool(shouldSave: bool = True):
    """
    Begins the processing of the image with the given flags.\n
    If some flags are not set, it will request them from the user.
    If that cant be done, it will exit with an error message.

    Returns the finished conversion, so the tool can also be driven from code.
    """
    args = pParseArguments()
    config = buildConfig(args, shouldSave)

    pReportSetup(config)

    try:
        return midend.execute(config)
    except tools.Errors.GenericError as e:
        exitWith(e)


def buildConfig(args: ap.Namespace, shouldSave: bool = True) -> Config:
    """
    Turns parsed arguments into a validated `Config`, prompting the user for anything
    missing that cannot be worked out on its own.
    """
    try:
        source = sources.openSource(args.inputFile, frameStep = args.inputFrameStep,
                                    maxFrames = args.inputMaxFrames)
    except tools.Errors.GenericError as e:
        exitWith(e)

    outputPath, outputType = pResolveOutput(
        args.inputFile, args.inputFilePathOut, args.inputFileTypeOut, args.inputFileNameOut
    )

    writeFrames = args.inputFrames
    pValidateCombination(args, source, outputType, writeFrames)

    charSet, charList = pResolveCharSet(args)
    widthCount, heightCount = pResolveGrid(args, pFirstFrameSize(source))

    return Config(
        source          =   source,
        sourcePath      =   args.inputFile,
        outputPath      =   outputPath,
        outputType      =   outputType,
        widthCount      =   widthCount,
        heightCount     =   heightCount,
        backend         =   compute.getBackend(args.inputGpu),
        colored         =   args.inputColored,
        pixelated       =   args.inputPixelated,
        charSet         =   charSet,
        charList        =   charList,
        invert          =   args.inputInvert,
        threshold       =   args.inputThreshold,
        band            =   tuple(sorted(args.inputBand)) if args.inputBand else None,
        dither          =   args.inputDither,
        edges           =   args.inputEdges,
        edgeSensitivity =   args.inputEdgeSensitivity,
        alpha           =   args.inputAlpha,
        printToScreen   =   args.inputPrint,
        # Printing on its own is not meant to litter the working directory with files.
        shouldSave      =   shouldSave and (not args.inputPrint or args.inputFilePathOut is not None),
        writeFrames     =   writeFrames,
        fps             =   args.inputFps,
    )


# What to change, in flags, for each rule `config.validateCombination` can break. The rules
# themselves are shared with the GUI; only this advice is particular to the command line.
CLI_REMEDIES = {
    'pixelartNeedsPicture':
        lambda: f"\tPick one of: {', '.join(t.lower() for t in tools.ValidTypes.getImageTypes())}, gif, mp4",
    'cannotPrintBinary':
        lambda: "\tDrop -p, or pick a text output type.",
    'animatedNeedsAnimatedOutput':
        lambda: ("\tPick an animated output type -> -ot gif   (or -ot mp4)\n"
                 "\tor write every frame separately -> --frames\n"
                 "\tor play it in the terminal -> -p\n"
                 "\tor convert a single frame -> --maxframes 1"),
    'framesAreAlreadyHeld':
        lambda: "\tDrop --frames, or pick a single-frame output type such as png or txt.",
    'stillCannotBeVideo':
        lambda: "\tPick an image output type, or use -ot gif for a one frame animation.",
}


def pValidateCombination(args: ap.Namespace, source: sources.FrameSource,
                         outputType: tools.ValidTypes, writeFrames: bool) -> None:
    """
    --- Private method! ---\n
    Rejects flag combinations that cannot produce a file, explaining what would work.

    The rules live in `config` so that both frontends enforce the same ones. What belongs
    here is the advice, because these are all cases where the user clearly wants something
    reasonable and simply picked the wrong pair of flags for it, and naming the flags to
    change is only useful to someone who is using flags.
    """
    try:
        config.validateCombination(
            outputType,
            isAnimated      =   source.isAnimated,
            frameCount      =   source.frameCount,
            sourceName      =   source.path.name,
            pixelated       =   args.inputPixelated,
            printToScreen   =   args.inputPrint,
            writeFrames     =   writeFrames,
        )
    except config.CombinationError as e:
        remedy = CLI_REMEDIES.get(e.reason)
        exitWith(f"{e.errorMsg}\n{remedy()}" if remedy else e.errorMsg)


def pFirstFrameSize(source: sources.FrameSource) -> tuple[int, int]:
    """
    --- Private method! ---\n
    The pixel size of the frames, which every frame is assumed to share.

    Read from the source's own metadata rather than by looking at a frame. A video decodes
    in one direction only, so peeking at the first frame to measure it would consume it,
    which silently dropped that frame from the conversion and then failed outright once
    the decoder had been advanced past the start.
    """
    return source.size


def pParseArguments() -> ap.Namespace:
    """
    --- Private method! ---\n
    Runs the parser, letting --help and --version exit quietly while still pausing on a
    real error, which matters when the tool was launched by double clicking it.
    """
    try:
        return parser.parse_args()
    except SystemExit as e:
        if e.code:
            exitWith("Invalid input. Run with -h for the full list of flags.")
        raise


def pOpenImage(path: pl.Path) -> Image.Image:
    """
    --- Private method! ---\n
    Opens the input image, reporting the usual failures in a readable way.
    """
    try:
        return Image.open(path)
    except FileNotFoundError:
        exitWith(f"File path was not found -> {path}")
    except UnidentifiedImageError:
        exitWith(f"File is not an image, or is in a format Pillow cannot read -> {path}")
    except OSError as e:
        exitWith(f"Could not read the input file -> {path}\n\t{e}")


def pResolveCharSet(args: ap.Namespace) -> tuple[tools.CharSet, str]:
    """
    --- Private method! ---\n
    Turns whichever of the three character flags was given into a set and its ramp.

    The choosing itself is shared with the GUI, so that adding a character set only has to
    be taught to one of them. All that happens here is naming the flag in the error.
    """
    try:
        return config.resolveCharSet(
            charsetName =   args.inputCharSet,
            customRamp  =   args.inputGrayscale,
            rampSize    =   args.inputGSCount,
        )
    except tools.Errors.GenericError as e:
        if args.inputGrayscale is not None:
            exitWith("The custom grayscale ramp given with -gs is empty!")
        exitWith(e.errorMsg)


def pResolveGrid(args: ap.Namespace, imgSize: tuple[int, int]) -> tuple[int, int]:
    """
    --- Private method! ---\n
    Works out the tile counts for both axes.

    An axis given explicitly is used as-is. A missing axis is derived from the other one
    and the character aspect ratio when --auto is set, and asked for otherwise. When both
    are missing, --auto sizes the output to the terminal.
    """
    imgWidth, imgHeight = imgSize

    widthCount = pResolveAxis(args.inputWidthPixel, args.inputWidthCount, imgWidth, 'width')
    heightCount = pResolveAxis(args.inputHeightPixel, args.inputHeightCount, imgHeight, 'height')

    if widthCount and heightCount:
        return widthCount, heightCount

    if not args.inputAuto:
        if not widthCount:
            widthCount = pPromptForTileCount(imgWidth, 'width')
        if not heightCount:
            heightCount = pPromptForTileCount(imgHeight, 'height')
        return widthCount, heightCount

    aspect = args.inputCharAspect

    if not widthCount and not heightCount:
        widthCount = min(shutil.get_terminal_size(fallback = (120, 30)).columns - 1, imgWidth)
        widthCount = max(widthCount, 1)

    if not heightCount:
        heightCount = round(widthCount * aspect * imgHeight / imgWidth)
    elif not widthCount:
        widthCount = round(heightCount * imgWidth / (aspect * imgHeight))

    widthCount = min(max(widthCount, 1), imgWidth)
    heightCount = min(max(heightCount, 1), imgHeight)

    print(f"\nAuto sizing chose a {widthCount} x {heightCount} tile grid "
          f"(character aspect ratio {aspect}).")

    return widthCount, heightCount


def pResolveAxis(pixelsPerTile: int | None, tileCount: int | None, imgSize: int, axisName: str) -> int | None:
    """
    --- Private method! ---\n
    Turns whichever of the two size flags was given for one axis into a tile count.
    Returns None when neither was given, leaving the decision to the caller.
    """
    if pixelsPerTile is None and tileCount is None:
        return None

    given = pixelsPerTile if pixelsPerTile is not None else tileCount
    if not 1 <= given <= imgSize:
        print(f"\nInput arguments for {axisName} are Invalid! "
              f"Expected a value between 1 and {imgSize}, got {given}.")
        given = pPromptForTileCount(imgSize, axisName)
        if pixelsPerTile is not None:
            return ceil(imgSize / given)
        return given

    if pixelsPerTile is not None:
        return ceil(imgSize / pixelsPerTile)

    return tileCount


def pPromptForTileCount(imgSize: int, axisName: str) -> int:
    """
    --- Private method! ---\n
    If the tile size flags were not set upon execution, this will prompt the user to specify them.
    """
    divisors = tools.pGetDivisors(imgSize)
    shown = divisors[:MAX_LISTED_DIVISORS]

    print(f"\nInput the desired tile {axisName} size in pixels. Integer divisors of the image {axisName}:")
    print(shown if len(shown) == len(divisors) else f"{shown} ... (+{len(divisors) - len(shown)} more)")
    print("A value that is not a divisor also works, the last tile just takes up the remainder.")

    while True:
        try:
            given = int(input())
        except ValueError:
            print(f"That is not a whole number. Input a valid integer within the bounds: [1-{imgSize}]!")
            continue
        except (EOFError, KeyboardInterrupt, OSError):
            exitWith("User issued an exit command during input dialogue.")

        if 1 <= given <= imgSize:
            return given

        print(f"Input a valid integer within the bounds: [1-{imgSize}]!")


def pResolveOutput(sourcePath: pl.Path, outPath: pl.Path | None,
                   fileType: str, nameMode: str) -> tuple[pl.Path, tools.ValidTypes]:
    """
    --- Private method! ---\n
    Works out where the result is written and in what format.

    With no -op, the file lands in the working directory under either the input file's name
    or a generated one. With -op, that path is used and the format's extension is appended
    if it is not already there. Missing parent folders are created either way.
    """
    outputType = tools.ValidTypes.fromExtension(fileType)
    suffix = f".{outputType.name.lower()}"

    if outPath is None:
        stem = sourcePath.stem if nameMode == 'INPUT' else tools.pGetUniqueName()
        target = pl.Path.cwd() / (stem + suffix)
    else:
        target = outPath if outPath.is_absolute() else pl.Path.cwd() / outPath
        if target.suffix.lower() != suffix:
            target = target.with_name(target.name + suffix)

    try:
        target.parent.mkdir(parents = True, exist_ok = True)
    except OSError as e:
        exitWith(f"Could not create the output folder -> {target.parent}\n\t{e}")

    return target, outputType


def pReportSetup(config: Config) -> None:
    """
    --- Private method! ---\n
    Prints what the tool is about to do, so the numbers can be sanity checked before a
    long conversion starts.
    """
    imgWidth, imgHeight = pFirstFrameSize(config.source)
    tileWidth = imgWidth / config.widthCount
    tileHeight = imgHeight / config.heightCount

    print(f"\nInput image dimensions (w x h): {imgWidth} x {imgHeight} pixels")
    print(f"Using tile size in pixels (w x h): {tileWidth:.2f} x {tileHeight:.2f}")
    print(f"Total tile count \n\tPer axis (w x h): {config.widthCount} x {config.heightCount}"
          f"\n\tTotal tiles: {config.widthCount * config.heightCount}")

    if config.charSet is not None and config.charSet.isSubCell:
        dotRows, dotCols = config.charSet.subShape
        print(f"Character set: {config.charSet.name} "
              f"({dotCols}x{dotRows} dots per cell, {config.widthCount * dotCols} x "
              f"{config.heightCount * dotRows} effective resolution)")

    if config.isAnimated:
        print(f"Animation: {config.frameCount} frames of {config.source.frameCount} being converted")

    print(f"Compute device: {config.backend.deviceName}\n")


def pIntInRange(low: int, high: int):
    """
    --- Private method! ---\n
    argparse type that rejects out of range integers with a readable message.
    """
    def parse(value: str) -> int:
        try:
            given = int(value)
        except ValueError:
            raise ap.ArgumentTypeError(f"'{value}' is not a whole number")
        if not low <= given <= high:
            raise ap.ArgumentTypeError(f"{given} is outside the allowed range [{low}-{high}]")
        return given

    return parse


def pFloatAbove(low: float):
    """
    --- Private method! ---\n
    argparse type for a float that has to be greater than `low`.
    """
    def parse(value: str) -> float:
        try:
            given = float(value)
        except ValueError:
            raise ap.ArgumentTypeError(f"'{value}' is not a number")
        if given <= low:
            raise ap.ArgumentTypeError(f"{given} must be greater than {low}")
        return given

    return parse


def exitWith(error: Exception | str | None = None) -> NoReturn:
    code = 0
    if error:
        print(f"\n{'-='*18} ERROR {'=-'*18}=\n\nDuring processing, program encountered an error with the "
              f"message:\n\t{error}\n\n{'-='*40}\n")
        # Non zero exit code indicates something went wrong
        code = 1

    try:
        input("\nPress 'Enter' to exit...\n")
    except (EOFError, KeyboardInterrupt, OSError):
        # No console to pause against, which is the normal case when the tool is being
        # piped, redirected or driven from a test.
        pass

    print("\nTool is exiting...\n")
    exit(code)
