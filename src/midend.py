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
Drives a conversion from end to end.

Pulls frames from the source, calls the backend to turn each one into a grid, hands the
grids to the writer for the chosen format, and puts the result on screen or on disk.
Anything format specific lives in `converters`; anything numeric lives in `backend`.

A still image is simply a one frame animation, so there is a single path through here
rather than two that have to be kept in step.
"""

import sys
import time

import numpy as np
import svg
from time import perf_counter
from typing import Any

from PIL import Image

from src import backend, converters, sources, tools
from src.converters import Conversion

# The two text formats can carry colour, but not in a way the user necessarily wants, so
# they get asked rather than having one behaviour picked for them.
TXT_COLOR_PROMPT = (
    "\tOutput only the ASCII characters -> t",
    "\tOutput colors and text in per-pixel format : [RRGGBBc RRGGBBc ...] -> c",
)
XML_COLOR_PROMPT = (
    "\tOutput only the ASCII characters, one element per row -> t",
    '\tOutput colors and text, one element per character : [<c f="#rrggbb">x</c> ...] -> c',
)

# Frame delay used when a source does not declare one.
DEFAULT_FRAME_DURATION_MS = 100.0

# How often to report progress, in frames. Often enough to show it is alive on a slow
# clip, rarely enough that it does not become the bottleneck on a fast one.
PROGRESS_EVERY = 10


# ================= Reporting ================

def pReport(config, message: str) -> None:
    """
    --- Private method! ---\n
    Says what the conversion is doing.

    Goes to standard output unless the caller supplied somewhere else to put it. A GUI has
    no terminal to print into and wants these lines in a log pane instead, so it passes a
    `log` and never sees them on stdout.
    """
    if config.log is not None:
        config.log(message)
        return

    print(message)


def pReportProgress(config, done: int, total: int) -> None:
    """
    --- Private method! ---\n
    Reports how far through a multi frame conversion we are.

    The terminal version rewrites one line in place, which a log pane cannot do, so a
    caller with a `progress` callback gets the two numbers and draws them however it likes.
    """
    if config.progress is not None:
        config.progress(done, total)
        return

    if config.log is None:
        print(f"\r\tFrame {done} of {total}...", end = '', flush = True)


# ================= Process ================

def execute(config) -> Conversion | Image.Image | list:
    """
    Runs the processing of the image or animation using the parameters on the given config.\n
    Returns the conversion itself for a still, or the list of them for an animation, so a
    caller that is not the CLI can use the result directly instead of reading it back off disk.\n
    Raises tools.Errors.GenericError if the requested combination cannot be honoured.
    """
    started = perf_counter()

    frames = pConvertFrames(config)

    config.backend.synchronize()
    elapsed = perf_counter() - started
    perFrame = f" ({elapsed / len(frames):.3f}s per frame)" if len(frames) > 1 else ""
    pReport(config, f"Converted {len(frames)} frame{'s' if len(frames) != 1 else ''} "
                    f"in {elapsed:.3f} seconds.{perFrame}")

    if config.isAnimated or config.writeFrames:
        pDeliverAnimation(frames, config)
    else:
        pDeliverStill(frames[0], config)

    return frames if len(frames) > 1 else frames[0]


def pConvertFrames(config) -> list:
    """
    --- Private method! ---\n
    Converts every frame the source yields.

    Progress is reported for anything long enough to be worth waiting for, because a video
    is thousands of times more work than a photo and silence looks like a hang.
    """
    results = []
    total = config.frameCount
    showProgress = total > 1

    with config.source as source:
        for index, frame in enumerate(source.frames()):
            image = backend.flattenAlpha(frame.image) if config.alpha else frame.image
            result = pRunPixelated(image, config) if config.pixelated else pRunAscii(image, config)

            if isinstance(result, Conversion):
                result.durationMs = frame.durationMs or DEFAULT_FRAME_DURATION_MS
            results.append(result)

            if showProgress and (index % PROGRESS_EVERY == 0 or index == total - 1):
                pReportProgress(config, index + 1, total)

    if showProgress and config.progress is None and config.log is None:
        print()

    if not results:
        raise tools.Errors.GenericError(f"No frames could be read from -> {config.sourcePath}")

    return results


def pRunAscii(image: Image.Image, config) -> Conversion:
    """
    --- Private method! ---\n
    Builds the character grid for one frame, and the matching colour grid when asked for.
    """
    charSet = config.charSet

    # Half blocks in colour are a special case: the character never changes, and the two
    # colours in each cell do all the work.
    if charSet is not None and charSet.needsColor and config.colored:
        chars, foreground, background = backend.toHalfBlockColors(
            image, config.widthCount, config.heightCount, config.backend
        )

        if config.band is not None:
            # Blanking the character is not enough here. Every cell also carries a
            # background colour, which fills it whatever character sits on top, so an
            # erased cell has to have both of its colours taken away as well.
            values = backend.toValueGrid(image.convert('L'), config.widthCount,
                                         config.heightCount, config.backend)
            keep = backend.bandMask(values, *config.band)

            chars = np.where(keep, chars, charSet.blank)
            empty = np.array(converters.BACKGROUND_DARK, dtype = background.dtype)
            foreground = np.where(keep[..., None], foreground, empty)
            background = np.where(keep[..., None], background, empty)

        return Conversion(chars, foreground, background)

    grayscale = image.convert('L')
    values = None

    if charSet is not None and charSet.isSubCell:
        chars = backend.toSubCellGrid(
            grayscale, config.widthCount, config.heightCount, charSet, config.backend,
            threshold = config.threshold, invert = config.invert,
            dither = config.dither, edgeSource = config.edges,
        )
    else:
        values = backend.toValueGrid(grayscale, config.widthCount, config.heightCount, config.backend)
        chars = backend.toCharGrid(values, config.charList, config.invert, config.threshold)

        if config.edges:
            magnitude, angle = backend.toEdgeGrids(
                grayscale, config.widthCount, config.heightCount, config.backend
            )
            chars = backend.applyEdges(chars, magnitude, angle, config.edgeSensitivity)

    if config.band is not None:
        # A sub-cell set works at several dots per cell and never builds a cell-sized value
        # grid of its own, so one is measured here. The band is about whole cells either
        # way: erasing individual dots would thin the picture out rather than cut holes in
        # it, which is not what taking a range of brightnesses away means.
        if values is None:
            values = backend.toValueGrid(grayscale, config.widthCount, config.heightCount, config.backend)

        low, high = config.band
        blank = charSet.blank if charSet is not None else ' '
        chars = backend.applyBand(chars, values, low, high, blank)

    colors = None
    if config.colored:
        colors = backend.toColorGrid(image, config.widthCount, config.heightCount, config.backend)

    return Conversion(chars, colors)


def pRunPixelated(image: Image.Image, config) -> Image.Image:
    """
    --- Private method! ---\n
    Builds the pixelart version of one frame. The colour channels are only converted when
    they are going to be used.
    """
    source = image.convert('RGB' if config.colored else 'L')
    blocks = backend.convert2Pixel(source, image.size, config.widthCount, config.heightCount)

    if config.band is None:
        return blocks

    values = backend.toValueGrid(image.convert('L'), config.widthCount,
                                 config.heightCount, config.backend)
    punched = backend.punchOutBand(blocks, values, *config.band)

    # JPEG has no alpha channel and video frames have nowhere to put one either, so for
    # those the holes are composited onto black rather than silently failing to save.
    if config.outputType in (tools.ValidTypes.JPG, tools.ValidTypes.MP4):
        return backend.flattenAlpha(punched)

    return punched


# ================= Delivery ================

def pDeliverStill(result: Conversion | Image.Image, config) -> None:
    """
    --- Private method! ---\n
    Renders and writes a single frame.
    """
    payload = pRenderOutput(result, config)

    if config.printToScreen:
        pPrintToScreen(payload, result, config)

    if config.shouldSave:
        save(payload, config)


def pDeliverAnimation(frames: list, config) -> None:
    """
    --- Private method! ---\n
    Renders and writes a whole sequence, in whichever of the four ways was asked for.
    """
    if config.printToScreen:
        pPlayInTerminal(frames, config)

    if not config.shouldSave:
        return

    if config.writeFrames:
        pSaveNumberedFrames(frames, config)
    elif config.outputType == tools.ValidTypes.GIF:
        pSaveAnimatedGIF(frames, config)
    elif config.outputType == tools.ValidTypes.MP4:
        pSaveVideo(frames, config)
    else:
        # The frontend rules this out, so reaching here means the rules and the writers
        # have drifted apart rather than the user having done anything wrong.
        raise tools.Errors.VariableInvalidValueError(
            'outputType', config.outputType, "No animated writer for this format!"
        )


def pSaveNumberedFrames(frames: list, config) -> None:
    """
    --- Private method! ---\n
    Writes one file per frame into a subfolder beside the output path.

    The folder and the count are announced before anything is written, so a directory
    filling up with hundreds of files is never a surprise.
    """
    suffix = f".{config.outputType.name.lower()}"
    folder = config.outputPath.with_suffix('').with_name(config.outputPath.stem + '_frames')

    pReport(config, f"\nWriting {len(frames)} frames as separate files.")
    pReport(config, f"\tInto folder: {folder}")
    pReport(config, f"\tNamed: frame_0001{suffix} ... frame_{len(frames):04d}{suffix}")

    try:
        folder.mkdir(parents = True, exist_ok = True)
    except OSError as e:
        raise tools.Errors.GenericError(f"Could not create the frames folder -> {folder}\n\t{e}")

    width = max(4, len(str(len(frames))))
    for index, frame in enumerate(frames, start = 1):
        target = folder / f"frame_{index:0{width}d}{suffix}"
        pWritePayload(pRenderOutput(frame, config), target, config.outputType)

    pReport(config, f"\nSaved {len(frames)} files to {folder}")


def pSaveAnimatedGIF(frames: list, config) -> None:
    """
    --- Private method! ---\n
    Writes the sequence as an animated GIF. Needs nothing beyond Pillow.
    """
    images = [frame if isinstance(frame, Image.Image) else converters.convertToIMG(frame)
              for frame in frames]
    durations = [pFrameDuration(frame, config) for frame in frames]

    try:
        images[0].save(config.outputPath, format = 'GIF', save_all = True,
                       append_images = images[1:], duration = durations, loop = 0, optimize = False)
    except OSError as e:
        raise tools.Errors.GenericError(f"Could not write the output file -> {config.outputPath}\n\t{e}")

    pReport(config, f"\nSaved {len(images)} frame animation to {config.outputPath}")


def pSaveVideo(frames: list, config) -> None:
    """
    --- Private method! ---\n
    Writes the sequence as a video, using whichever optional backend is installed.
    """
    images = [frame if isinstance(frame, Image.Image) else converters.convertToIMG(frame)
              for frame in frames]
    fps = config.fps or pAverageFps(frames, config)

    pReport(config, f"\nEncoding {len(images)} frames at {fps:.2f} fps...")
    encoder = sources.writeVideo(config.outputPath, images, fps)

    pReport(config, f"Saved video to {config.outputPath} (encoded with {encoder})")


def pFrameDuration(frame, config) -> int:
    """
    --- Private method! ---\n
    How long one frame should be shown, in whole milliseconds.
    """
    if config.fps:
        return max(1, int(round(1000.0 / config.fps)))

    duration = getattr(frame, 'durationMs', 0) or DEFAULT_FRAME_DURATION_MS

    return max(1, int(round(duration)))


def pAverageFps(frames: list, config) -> float:
    """
    --- Private method! ---\n
    Works out a frame rate from the per-frame durations the source reported.
    """
    durations = [getattr(frame, 'durationMs', 0) or DEFAULT_FRAME_DURATION_MS for frame in frames]
    average = sum(durations) / len(durations)

    return 1000.0 / average if average else 10.0


def pPlayInTerminal(frames: list, config) -> None:
    """
    --- Private method! ---\n
    Plays the animation in place in the terminal, at the source's own timing.

    The cursor is hidden and restored around the loop, and the screen is redrawn from the
    top each frame rather than scrolled, which is what makes it look like playback rather
    than a wall of output.
    """
    rendered = [pRenderForScreen(frame, config) for frame in frames]
    delays = [pFrameDuration(frame, config) / 1000.0 for frame in frames]

    print(f"\nPlaying {len(rendered)} frames. Press Ctrl+C to stop.\n")
    time.sleep(0.4)

    try:
        sys.stdout.write(converters.ANSI_HIDE_CURSOR)
        while True:
            for lines, delay in zip(rendered, delays):
                sys.stdout.write(converters.ANSI_CLEAR_SCREEN)
                sys.stdout.write('\n'.join(lines))
                sys.stdout.flush()
                time.sleep(delay)

            if not pShouldLoop(config):
                break
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write(converters.ANSI_SHOW_CURSOR + converters.ANSI_RESET + '\n')
        sys.stdout.flush()


def pShouldLoop(config) -> bool:
    """
    --- Private method! ---\n
    Whether playback repeats. It does, unless the output is also being saved, in which
    case looping forever would stop the tool ever getting to the writing.
    """
    return not config.shouldSave


def pRenderForScreen(result, config) -> list[str]:
    """
    --- Private method! ---\n
    One frame as the list of lines to print.
    """
    if isinstance(result, Image.Image):
        raise tools.Errors.GenericError("Pixelart cannot be printed to the screen.")

    if config.colored:
        return converters.convertToAnsi(result)

    return result.asRows()


def pRenderOutput(result: Conversion | Image.Image, config) -> Any:
    """
    --- Private method! ---\n
    Hands one frame to the writer for the chosen output format.
    """
    if isinstance(result, Image.Image):
        # Pixelart is already a picture; the frontend has ruled out non-image formats.
        return result

    match config.outputType:
        case tools.ValidTypes.TXT:
            return converters.convertToText(result, pAskEmbedColor(config, 'txt', TXT_COLOR_PROMPT))
        case tools.ValidTypes.XML:
            return converters.convertToXML(result, pAskEmbedColor(config, 'xml', XML_COLOR_PROMPT))
        case tools.ValidTypes.SVG:
            return converters.convertToSVG(result)
        case tools.ValidTypes.JPG | tools.ValidTypes.PNG | tools.ValidTypes.GIF | tools.ValidTypes.MP4:
            return converters.convertToIMG(result)

    raise tools.Errors.VariableInvalidValueError('outputType', config.outputType, "No writer for this format!")


def pAskEmbedColor(config, formatName: str, options: tuple[str, ...]) -> bool:
    """
    --- Private method! ---\n
    Works out whether colour should be written into a text format, asking if need be.
    Raises if the user would rather stop than pick either way.

    A caller that already knows the answer says so on the config and is never asked. That
    is what lets the GUI drive this, since a prompt it cannot show is a prompt that hangs.
    Otherwise the question goes to the terminal, and the answer is remembered on the same
    field, so converting a thousand frame animation does not ask a thousand times.
    """
    if not config.colored:
        return False

    if config.embedColor is not None:
        return config.embedColor

    print(f"\nInput flag {{ -c : Colored }} was set, but output type is .{formatName}! Choose one of the following:")
    for option in options:
        print(option)
    print("\tExit without proceeding -> e")

    while True:
        try:
            answer = input("Leave empty for default (e) : ").strip().lower()
        except (EOFError, KeyboardInterrupt, OSError):
            answer = 'e'

        if not answer:
            answer = 'e'

        # A membership test against a string would also accept 'tc' and every other
        # substring, then fall through every branch and silently write the wrong thing.
        if answer in ('t', 'c', 'e'):
            break

        print("Please answer with exactly one of: t, c, e.")

    if answer == 'e':
        raise tools.Errors.GenericError(
            f"Colored flag was set, but output type was .{formatName}! User requested to exit."
        )

    print("Outputting only the ASCII characters." if answer == 't' else "Including colors in the output.")

    config.embedColor = answer == 'c'

    return config.embedColor


def pPrintToScreen(payload: Any, result, config) -> None:
    """
    --- Private method! ---\n
    Writes a single frame to standard output.
    """
    print()
    if isinstance(payload, svg.SVG):
        print(payload.as_str())
    elif config.colored and isinstance(result, Conversion):
        print('\n'.join(converters.convertToAnsi(result)))
    else:
        print('\n'.join(payload))
    print()


def save(data: Any, config) -> None:
    """
    Saves the data to the output file.
    """
    pWritePayload(data, config.outputPath, config.outputType)

    pReport(config, f"\nSaved file to {config.outputPath}")


def pWritePayload(data: Any, path, outputType: tools.ValidTypes) -> None:
    """
    --- Private method! ---\n
    Writes one payload to one path.

    Text formats and picture formats are written by completely different code, so the file
    is only opened on the branch that actually needs a text handle. Opening one for every
    format, as this used to, meant truncating the path out from under Pillow.
    """
    try:
        if isinstance(data, Image.Image):
            data.save(path, 'JPEG' if outputType == tools.ValidTypes.JPG else outputType.name)
        elif isinstance(data, svg.SVG):
            path.write_text(data.as_str(), encoding = 'utf-8')
        else:
            path.write_text('\n'.join(data) + '\n', encoding = 'utf-8')
    except OSError as e:
        raise tools.Errors.GenericError(f"Could not write the output file -> {path}\n\t{e}")
