###########################################################################
# Copyright (c) 2024, Andy Pandy                                          #
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
