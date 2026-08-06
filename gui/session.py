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
Turning what the panel says into what the engine wants.

This is the GUI's answer to `frontend.buildConfig`, and the only place in the GUI that
knows what a `Config` is. Nothing here imports Qt, so the translation can be tested without
a window on screen.
"""

import pathlib as pl
from math import ceil

from PIL import Image

from src import compute, config as configModule, converters, midend, sources, tools

# A preview runs on one frame however long the clip is. Waiting for a thousand frames to
# find out that the threshold is slightly too high is not previewing, it is converting.
PREVIEW_FRAMES = 1


def firstFrame(path: pl.Path) -> tuple[Image.Image, bool, int, tuple[int, int]]:
    """
    Opens a file just far enough to show it and describe it.

    Returns the opening frame, whether there are more, how many there are, and the pixel
    size. A video is read through the same `sources` machinery as everything else, so a
    format the converter can handle is a format the preview can show.
    """
    source = sources.openSource(path, maxFrames = 1)

    with source as opened:
        frames = list(opened.frames())

        if not frames:
            raise tools.Errors.GenericError(f"No frames could be read from -> {path}")

        # Copied before the block ends. Closing the source closes the file Pillow is
        # reading through, and a lazily loaded frame is unusable the moment that happens.
        image = frames[0].image.convert('RGB')

    return image, source.isAnimated, source.frameCount, source.size


def tileCounts(settings: dict, imageSize: tuple[int, int]) -> tuple[int, int]:
    """
    The two axes as tile counts, whichever way round the panel expressed them.

    A pixels-per-tile value becomes a count the same way the CLI does it, by dividing and
    rounding up so the last tile takes the remainder rather than being dropped.
    """
    imgWidth, imgHeight = imageSize

    def resolve(mode: str, value: int, extent: int) -> int:
        count = ceil(extent / value) if mode == 'pixels' else value

        return max(1, min(count, extent))

    return (
        resolve(settings['widthMode'], settings['widthValue'], imgWidth),
        resolve(settings['heightMode'], settings['heightValue'], imgHeight),
    )


def buildConfig(settings: dict, inputPath: pl.Path, outputPath: pl.Path, *,
                shouldSave: bool, preview: bool = False,
                progress = None, log = None) -> configModule.Config:
    """
    Assembles a `Config` from the panel's settings.

    The source is opened here, on every call, and never reused. `midend` closes whatever
    source it is handed, and a video decodes in one direction only, so a config that has
    been run once cannot be run again.

    Raises `tools.Errors.GenericError` for anything that cannot be honoured, including the
    shared combination rules, which the caller is expected to put in front of the user.
    """
    maxFrames = PREVIEW_FRAMES if preview else settings['maxFrames']

    source = sources.openSource(
        inputPath,
        frameStep = settings['frameStep'],
        maxFrames = maxFrames,
    )

    outputType = tools.ValidTypes.fromExtension(settings['outputType'])
    pixelated = settings['charMode'] == 'pixelart'
    writeFrames = settings['writeFrames'] and not preview

    # A preview writes nothing, so the rules about what can be written to a file do not
    # apply to it. They are still enforced for the real conversion, from the same place
    # the CLI enforces them.
    if not preview:
        configModule.validateCombination(
            outputType,
            isAnimated      =   source.isAnimated,
            frameCount      =   source.selectedCount,
            sourceName      =   inputPath.name,
            pixelated       =   pixelated,
            writeFrames     =   writeFrames,
        )

    charSet, charList = pResolveCharacters(settings)
    widthCount, heightCount = tileCounts(settings, source.size)

    return configModule.Config(
        source          =   source,
        sourcePath      =   inputPath,
        outputPath      =   outputPath,
        outputType      =   outputType,
        widthCount      =   widthCount,
        heightCount     =   heightCount,
        backend         =   compute.getBackend(settings['gpu']),
        colored         =   settings['colored'],
        pixelated       =   pixelated,
        charSet         =   charSet,
        charList        =   charList,
        invert          =   settings['invert'],
        threshold       =   settings['threshold'],
        band            =   settings['band'],
        dither          =   settings['dither'],
        edges           =   settings['edges'],
        edgeSensitivity =   settings['edgeSensitivity'],
        alpha           =   settings['alpha'],
        printToScreen   =   False,
        shouldSave      =   shouldSave,
        writeFrames     =   writeFrames,
        fps             =   settings['fps'],
        # Always decided up front. A GUI cannot answer a question asked through `input()`,
        # so leaving this unset is how the whole window would come to hang.
        embedColor      =   settings['embedColor'],
        progress        =   progress,
        log             =   log,
    )


def pResolveCharacters(settings: dict) -> tuple[tools.CharSet, str]:
    """
    --- Private method! ---\n
    The chosen character source, in the shared engine's terms.

    Pixel art uses no characters at all, but a `Config` still carries a set, so it gets the
    default ramp for the field to hold rather than a special case further down.
    """
    mode = settings['charMode']

    if mode == 'charset':
        return configModule.resolveCharSet(charsetName = settings['charsetName'])
    if mode == 'customRamp':
        return configModule.resolveCharSet(customRamp = settings['customRamp'])

    return configModule.resolveCharSet(rampSize = settings['rampSize'])


def pQuote(value) -> str:
    """
    --- Private method! ---\n
    One argument, safe to paste into a shell.

    Double quotes rather than the POSIX single quotes `shlex` would use, because the command
    being shown is one to run on the machine the window is running on, and on Windows single
    quotes are not quoting at all.
    """
    text = str(value)

    if text and not any(character in text for character in ' \t"\'&|<>^()'):
        return text

    return '"' + text.replace('"', r'\"') + '"'


def commandLine(settings: dict, inputPath: pl.Path, outputPath: pl.Path | None = None, *,
                preview: bool = False) -> str:
    """
    The same conversion written out as a command line.

    Shown in the log so that the window is never a black box: whatever it just did can be
    read, copied, scripted or pasted into a bug report. Only settings that are actually
    doing something appear, so the command stays the short one a person would have typed.

    Neither `-a` nor `-ca` is ever emitted. Both exist on the command line to work out tile
    counts that were not given, and the window always knows both counts, so it passes them
    outright. The aspect ratio is already baked into the numbers.
    """
    parts = ['python', 'converter.py', pQuote(inputPath)]

    widthFlag = '-wi' if settings['widthMode'] == 'pixels' else '-wc'
    heightFlag = '-hi' if settings['heightMode'] == 'pixels' else '-hc'
    parts += [widthFlag, str(settings['widthValue']), heightFlag, str(settings['heightValue'])]

    mode = settings['charMode']
    if mode == 'pixelart':
        parts.append('-pix')
    elif mode == 'charset':
        parts += ['-cs', settings['charsetName']]
    elif mode == 'customRamp':
        parts += ['-gs', pQuote(settings['customRamp'])]
    elif settings['rampSize'] != 70:
        parts += ['-gsc', str(settings['rampSize'])]

    for flag, wanted in (('-c', settings['colored']), ('-i', settings['invert']),
                         ('-d', settings['dither']), ('--alpha', settings['alpha']),
                         ('-e', settings['edges'])):
        if wanted:
            parts.append(flag)

    if settings['edges'] and settings['edgeSensitivity'] != 90:
        parts += ['-et', str(settings['edgeSensitivity'])]

    if settings['threshold'] is not None:
        parts += ['-th', str(settings['threshold'])]

    if settings['band'] is not None:
        low, high = settings['band']
        parts += ['-tb', str(low), str(high)]

    if settings['gpu']:
        parts += ['-g', settings['gpu']]

    # A preview is one frame of whatever it was given, so that is what the command says.
    if preview:
        parts += ['--maxframes', str(PREVIEW_FRAMES)]
    elif settings['maxFrames'] is not None:
        parts += ['--maxframes', str(settings['maxFrames'])]

    if settings['frameStep'] != 1:
        parts += ['--framestep', str(settings['frameStep'])]
    if settings['fps'] is not None:
        parts += ['--fps', str(settings['fps'])]
    if settings['writeFrames'] and not preview:
        parts.append('--frames')

    parts += ['-ot', settings['outputType']]

    if outputPath is not None and not preview:
        parts += ['-op', pQuote(outputPath)]

    return ' '.join(parts)


def commandNotes(settings: dict, preview: bool = False) -> list[str]:
    """
    Anything about the command above that the flags cannot say on their own.

    There is one: colour into a text format is a question the command line asks while it
    runs, and the window has already answered it. Without this the command looks as though
    it would reproduce the result silently, and then it stops and waits for input.
    """
    notes = []

    if settings['colored'] and settings['outputType'] in ('txt', 'xml'):
        answer = 'c' if settings['embedColor'] else 't'
        notes.append(f"     ...and answers '{answer}' when it asks about colour in "
                     f"{settings['outputType'].upper()}.")

    if preview:
        notes.append("     (preview: nothing is written until you use Convert & Save)")

    return notes


def renderForDisplay(result, config, asPicture: bool) -> tuple[str, object]:
    """
    One converted frame, ready to put in the result pane.

    Returns ('image', PIL image) or ('text', str). Text formats can be shown either way:
    as the characters that will be written, or drawn as a picture so it lines up with the
    source next to it. Both come out of the same conversion, so the choice costs nothing
    and does not affect what gets saved.
    """
    frame = result[0] if isinstance(result, list) else result

    if isinstance(frame, Image.Image):
        return 'image', frame

    if asPicture:
        return 'image', converters.convertToIMG(frame)

    # Whatever the writer for this format would produce, rather than a second guess at it.
    payload = midend.pRenderOutput(frame, config)

    if isinstance(payload, Image.Image):
        return 'image', payload
    if hasattr(payload, 'as_str'):
        return 'text', payload.as_str()

    return 'text', '\n'.join(payload)
