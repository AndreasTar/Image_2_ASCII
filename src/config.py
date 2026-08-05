###########################################################################
# Copyright (c) 2024, Andy Pandy                                          #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################

"""
What a conversion is, independent of who asked for it.

This used to live in `frontend.py`, which made the command line the only thing that could
describe a conversion. It sits on its own now because there are two frontends: the CLI
builds a `Config` out of argparse, the GUI builds one out of its controls, and the midend
cannot tell the difference.

Nothing here imports either frontend, which is what keeps that true.
"""

import pathlib as pl
from dataclasses import dataclass
from typing import Callable

from src import compute, sources, tools

# Percentile of gradient strength above which a cell is drawn as an edge. 90 keeps the
# strongest tenth, which reads well on both line art and photographs.
DEFAULT_EDGE_SENSITIVITY = 90


@dataclass
class Config:
    """
    Everything the conversion needs, resolved and validated.

    Replaces the old class-as-singleton, where every field was written onto the class
    itself and shared by every conversion in the process.
    """

    source: sources.FrameSource
    sourcePath: pl.Path
    outputPath: pl.Path
    outputType: tools.ValidTypes
    widthCount: int
    heightCount: int
    backend: compute.ComputeBackend

    colored: bool = False
    pixelated: bool = False
    charSet: tools.CharSet = None
    charList: str = tools.GRAYSCALES[70]
    invert: bool = False
    threshold: int | None = None
    # A brightness band to keep, as (low, high). Everything outside it is erased: a blank
    # character, or a transparent block in pixel art. Everything inside is left exactly as
    # it would have been with no band at all, which is what separates this from `threshold`
    # above — that one rewrites every value, this one only decides what survives.
    band: tuple[int, int] | None = None
    dither: bool = False
    edges: bool = False
    edgeSensitivity: float = DEFAULT_EDGE_SENSITIVITY
    alpha: bool = False
    printToScreen: bool = False
    shouldSave: bool = True
    writeFrames: bool = False
    fps: float | None = None

    # Whether colour is written into the two text formats, which can carry it but not
    # necessarily in a way the user wants. `None` means nobody has decided yet, and the CLI
    # takes that as its cue to ask. A caller with no terminal to ask through, such as the
    # GUI, sets it either way up front and is never prompted.
    embedColor: bool | None = None

    # Where the midend reports to. Left unset, it prints, which is what the CLI wants.
    # A GUI passes its own, so the same conversion drives a progress bar and a log pane
    # instead of a terminal.
    progress: Callable[[int, int], None] | None = None   # (framesDone, framesTotal)
    log: Callable[[str], None] | None = None

    @property
    def isAnimated(self) -> bool:
        return self.source.isAnimated

    @property
    def frameCount(self) -> int:
        return self.source.selectedCount


def resolveCharSet(charsetName: str | None = None, customRamp: str | None = None,
                   rampSize: int = 70) -> tuple[tools.CharSet, str]:
    """
    Picks how characters get chosen: a named set, a custom ramp, or a built-in ramp size.

    Returns the set and its ramp. The ramp is meaningless for the sub-cell sets, which
    build their characters from bits rather than looking them up, so it stays at the
    default there purely so the rest of the config has something sensible in it.

    Raises `tools.Errors.GenericError` rather than reporting anything, because a frontend
    with no terminal still has to be able to catch this.
    """
    if charsetName is not None:
        charSet = tools.CHARSETS[charsetName]
        return charSet, charSet.ramp or tools.GRAYSCALES[70]

    if customRamp is not None:
        if not customRamp:
            raise tools.Errors.GenericError("The custom grayscale ramp is empty!")
        return tools.CharSet('custom', ramp = customRamp), customRamp

    if rampSize not in tools.GRAYSCALES:
        raise tools.Errors.GenericError(
            f"Invalid Grayscale size used: {rampSize}! Valid sizes are: {sorted(tools.GRAYSCALES)}"
        )

    ramp = tools.GRAYSCALES[rampSize]

    return tools.CharSet(f'ascii{rampSize}', ramp = ramp), ramp


class CombinationError(tools.Errors.GenericError):
    """
    A set of settings that cannot produce a file.

    `reason` names which rule was broken, so a frontend can add advice in its own terms.
    The CLI answers with the flags to change; the GUI has controls to point at instead, and
    neither wants the other's wording.
    """

    def __init__(self, reason: str, error_msg: str) -> None:
        self.reason = reason

        super().__init__(error_msg)


def validateCombination(outputType: tools.ValidTypes, *, isAnimated: bool, frameCount: int,
                        sourceName: str, pixelated: bool = False, printToScreen: bool = False,
                        writeFrames: bool = False) -> None:
    """
    Rejects settings that cannot produce a file, saying what is wrong but not how to fix it.

    These are the rules themselves, kept away from either frontend so that there is one
    definition of what is legal rather than one per way of asking. Raises `CombinationError`.
    """
    if pixelated and not outputType.isImage() and not outputType.isAnimated():
        raise CombinationError(
            'pixelartNeedsPicture',
            f"Pixelart cannot be written as {outputType.name}, because it is a picture "
            f"rather than characters."
        )

    if printToScreen and (outputType.isImage() or outputType == tools.ValidTypes.MP4):
        raise CombinationError(
            'cannotPrintBinary',
            f"{outputType.name} cannot be shown as text on a screen."
        )

    if isAnimated and not (outputType.isAnimated() or writeFrames or printToScreen):
        raise CombinationError(
            'animatedNeedsAnimatedOutput',
            f"{sourceName} has {frameCount} frames, but {outputType.name} holds only one."
        )

    if writeFrames and outputType.isAnimated():
        raise CombinationError(
            'framesAreAlreadyHeld',
            f"That writes one file per frame, but {outputType.name} already holds them all."
        )

    if not isAnimated and outputType == tools.ValidTypes.MP4:
        raise CombinationError(
            'stillCannotBeVideo',
            f"{sourceName} is a single image, so there is nothing to make a video from."
        )
