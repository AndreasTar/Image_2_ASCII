###########################################################################
# Copyright (c) 2024, Andy Pandy                                          #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################

"""
All the maths the tool needs, in vectorised form.

Everything here works on whole grids at once rather than one tile at a time, which is
what makes the tool fast, and is also what lets the same code run on a GPU.

The single definition every function is built on is the *block mean*: the image is split
into `rows` x `cols` tiles whose edges fall on rounded integer pixel boundaries, and each
tile becomes the average of the pixels inside it. Two implementations of that definition
live here and they agree to within float rounding:

  - CPU: segmented sums with `np.add.reduceat`, which reduces straight to the tile grid.
  - Device: a cumulative-sum (summed-area) reduction, written with the small set of
    operations `compute.ComputeBackend` exposes, so it runs on NumPy, CuPy or PyTorch.

Pillow's BOX resampling looks like a drop-in for the CPU half and is about twice as quick,
but it is not reliably a block mean: on some image and grid size combinations it returns
tile averages off by around 11 grayscale levels, which is several characters' worth. It is
deliberately not used here. See tests/test_backend.py::testMatchesExactBlockMean.
"""

import numpy as np
from PIL import Image

from src import tools
from src.compute import ComputeBackend

# Sobel gradients reach +/- 4 * 255 per axis. Dividing by this brings the magnitude back
# into a 0-255 range.
EDGE_SCALE = 4.0

# Gradient angles are bucketed into this many directions, one per entry of tools.EDGE_CHARS.
EDGE_DIRECTIONS = len(tools.EDGE_CHARS)

# Cells quieter than this are never treated as edges, however weak the rest of the image
# is. Without it a flat image would have its own noise promoted into edge characters.
MIN_EDGE_MAGNITUDE = 2.0


def toValueGrid(image: Image.Image, cols: int, rows: int, backend: ComputeBackend) -> np.ndarray:
    """
    Reduces a single channel image to a `rows` x `cols` grid of brightness values in 0-255.

    This is the tool's core operation. Returns a host (NumPy) array regardless of device.
    """
    pValidateGrid(image.size, cols, rows)
    pixels = np.asarray(image, dtype = np.float32)

    if not backend.usesDeviceArrays:
        return pBlockMeanNumpy(pixels, cols, rows)

    return backend.toHost(pBlockMeanDevice(backend.asarray(pixels), cols, rows, backend))


def toColorGrid(image: Image.Image, cols: int, rows: int, backend: ComputeBackend) -> np.ndarray:
    """
    Reduces an image to a `rows` x `cols` x 3 grid of averaged RGB values.

    The image is converted to RGB first, so palette, grayscale and RGBA inputs all work.
    Returns a host uint8 array.
    """
    pValidateGrid(image.size, cols, rows)
    rgb = image if image.mode == 'RGB' else image.convert('RGB')
    pixels = np.asarray(rgb, dtype = np.float32)

    if not backend.usesDeviceArrays:
        channels = [pBlockMeanNumpy(pixels[:, :, c], cols, rows) for c in range(3)]
    else:
        device = backend.asarray(pixels)
        channels = [backend.toHost(pBlockMeanDevice(device[:, :, c], cols, rows, backend)) for c in range(3)]

    return np.clip(np.stack(channels, axis = -1), 0, 255).astype(np.uint8)


def toEdgeGrids(image: Image.Image, cols: int, rows: int,
                backend: ComputeBackend) -> tuple[np.ndarray, np.ndarray]:
    """
    Runs Sobel edge detection at full resolution and reduces the result per tile.

    Gradients are computed over every pixel and then block-averaged, rather than being
    computed on the already-reduced grid, so thin lines still register.

    Strength and direction are reduced differently on purpose. Strength comes from
    averaging the magnitude, which is never negative and so cannot cancel itself out;
    averaging the two components and taking the magnitude of that instead would quietly
    erase any edge that curves inside a single tile. Direction does come from the averaged
    components, because that is the only form that still carries a sign.

    Returns (magnitude, angle): magnitude on a 0-255 scale, angle in radians.
    This is the most expensive stage in the tool and the one that benefits most from --gpu.
    """
    pValidateGrid(image.size, cols, rows)

    pixels = backend.asarray(np.asarray(image, dtype = np.float32))
    gradX, gradY = pSobel(pixels, backend)
    strength = backend.hypot(gradX, gradY)

    if not backend.usesDeviceArrays:
        magnitude, meanX, meanY = (pBlockMeanNumpy(g, cols, rows) for g in (strength, gradX, gradY))
    else:
        magnitude, meanX, meanY = (backend.toHost(pBlockMeanDevice(g, cols, rows, backend))
                                   for g in (strength, gradX, gradY))

    return np.clip(magnitude / EDGE_SCALE, 0, 255), np.arctan2(meanY, meanX)


def toCharGrid(values: np.ndarray, charList: str,
               invert: bool = False, threshold: int | None = None) -> np.ndarray:
    """
    Maps a grid of 0-255 brightness values onto characters from `charList`.

    `charList` runs densest to lightest, so dark areas get the heavy characters. `invert`
    flips that, putting the heavy characters on the bright areas instead. `threshold`
    collapses everything to the two extremes at the given cutoff.
    """
    if not charList:
        raise tools.Errors.VariableInvalidValueError('charList', charList, "The character ramp cannot be empty!")

    levels = np.clip(values, 0, 255).astype(np.float32)

    if threshold is not None:
        levels = np.where(levels >= threshold, 255.0, 0.0)
    if invert:
        levels = 255.0 - levels

    ramp = np.array(list(charList))
    indices = (levels * (len(ramp) - 1) / 255.0).astype(np.int32)

    return ramp[indices]


def applyEdges(chars: np.ndarray, magnitude: np.ndarray, angle: np.ndarray, sensitivity: float) -> np.ndarray:
    """
    Replaces characters with a directional line character wherever an edge was detected.

    The gradient points across the edge, so a gradient pointing right means a vertical
    edge. Bucketing the angle to the nearest 45 degrees picks one of tools.EDGE_CHARS.

    `sensitivity` is a percentile from 0 to 100, so `90` turns the strongest tenth of the
    image into edges. It is expressed that way because gradient strength depends entirely
    on the picture: a fixed cutoff that suits a hard edged drawing finds nothing at all on
    a soft photograph. MIN_EDGE_MAGNITUDE still applies underneath, so a flat image comes
    back with no edges rather than a percentile's worth of noise.
    """
    cutoff = max(float(np.percentile(magnitude, np.clip(sensitivity, 0, 100))), MIN_EDGE_MAGNITUDE)

    bucket = np.rint(angle / (np.pi / EDGE_DIRECTIONS)).astype(np.int32) % EDGE_DIRECTIONS
    edgeChars = np.array(list(tools.EDGE_CHARS))[bucket]

    return np.where(magnitude >= cutoff, edgeChars, chars)


def toSubCellGrid(image: Image.Image, cols: int, rows: int, charSet: tools.CharSet,
                  backend: ComputeBackend, threshold: int | None = None,
                  invert: bool = False, dither: bool = False,
                  edgeSource: bool = False) -> np.ndarray:
    """
    Renders with a sub-cell character set, such as braille or quadrant blocks.

    Each cell is split into `charSet.subShape` dots, every dot is decided on its own, and
    the results are packed into one character. That is what buys braille its eightfold
    resolution: the grid handed to `toValueGrid` is simply a multiple of the requested one.

    **Dark is ink.** A dot switches on where the image is dark, matching the ramp sets,
    where index 0 is the densest character. Inking the bright side instead would render a
    photograph as its own negative.

    `threshold` defaults to the mean of the sub-cell grid, because a fixed cutoff turns
    most photographs into a solid rectangle. `dither` trades that hard cutoff for an
    ordered pattern, which only reads as tone once the cells are small enough.
    `edgeSource` inks gradient strength instead of darkness, giving line art.
    """
    if not charSet.isSubCell:
        raise tools.Errors.VariableInvalidValueError('charSet', charSet.name, "This character set is not sub-cell!")

    dotRows, dotCols = charSet.subShape
    pValidateGrid(image.size, cols * dotCols, rows * dotRows)

    if edgeSource:
        # Gradient strength is already "more means more ink", so it needs no inverting.
        values, _ = toEdgeGrids(image, cols * dotCols, rows * dotRows, backend)
        ink = pInkMask(values, threshold, dither, defaultPercentile = 88.0,
                       minimum = MIN_EDGE_MAGNITUDE)
    else:
        values = toValueGrid(image, cols * dotCols, rows * dotRows, backend)
        ink = pInkMask(255.0 - values, threshold if threshold is None else 255 - threshold, dither)

    if invert:
        ink = ~ink

    weights = np.array(charSet.bitWeights, dtype = np.int32)
    packed = (ink.reshape(rows, dotRows, cols, dotCols) * weights[None, :, None, :]).sum(axis = (1, 3))

    characters = np.array([charSet.characterFor(value) for value in range(int(weights.sum()) + 1)])

    return characters[packed]


def toHalfBlockColors(image: Image.Image, cols: int, rows: int,
                      backend: ComputeBackend) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Renders in colour using the upper half block, which doubles the vertical resolution.

    Every cell is the same character. The work is done by the two colours: the upper half
    block paints the top of the cell in the foreground colour and leaves the bottom
    showing the background, so one character carries two independently coloured pixels.

    Returns (chars, foreground, background).
    """
    pValidateGrid(image.size, cols, rows * 2)

    doubled = toColorGrid(image, cols, rows * 2, backend)
    chars = np.full((rows, cols), tools.HALFBLOCK_CHARS[1])

    return chars, doubled[0::2], doubled[1::2]


def pInkMask(darkness: np.ndarray, threshold: float | None, dither: bool,
             defaultPercentile: float | None = None, minimum: float | None = None) -> np.ndarray:
    """
    --- Private method! ---\n
    Decides which dots are inked, given how dark each one is on a 0-255 scale.

    `minimum` is a floor the cutoff can never fall below. It matters for the edge path: a
    picture with no edges in it has a gradient of zero everywhere, and any percentile of
    all zeros is also zero, which would other wise ink every single dot.
    """
    if dither:
        # Tiling the Bayer matrix gives each dot its own cutoff, so a flat tone becomes an
        # even pattern whose density tracks the tone instead of snapping to all or nothing.
        matrix = np.array(tools.BAYER_MATRIX, dtype = np.float32)
        size = matrix.shape[0]
        scaled = (matrix + 0.5) / (size * size) * 255.0
        height, width = darkness.shape
        tiled = np.tile(scaled, (height // size + 1, width // size + 1))[:height, :width]

        return darkness > tiled

    if threshold is None:
        cutoff = float(np.percentile(darkness, defaultPercentile)) if defaultPercentile is not None \
                 else float(darkness.mean())
    else:
        cutoff = float(threshold)

    if minimum is not None:
        cutoff = max(cutoff, minimum)

    return darkness >= cutoff


def bandMask(values: np.ndarray, low: float, high: float) -> np.ndarray:
    """
    Which cells fall inside a brightness band, and so survive it.

    True is 'keep'. Both ends are inclusive, and a band given the wrong way round is read
    as the range between the two numbers rather than as an empty one, because a pair of
    sliders that have been dragged past each other is a slip rather than a request for a
    blank picture.
    """
    low, high = (low, high) if low <= high else (high, low)
    levels = np.clip(values, 0, 255)

    return (levels >= low) & (levels <= high)


def applyBand(chars: np.ndarray, values: np.ndarray, low: float, high: float,
              blank: str = ' ') -> np.ndarray:
    """
    Erases every cell whose brightness lies outside the band, leaving the rest untouched.

    Deliberately applied *after* the characters have been chosen, so that what is kept looks
    exactly as it would have with no band set at all. That is the whole point of it: unlike
    the two-tone threshold, which rewrites every value it is given, this one only decides
    what is there and what is not.
    """
    return np.where(bandMask(values, low, high), chars, blank)


def punchOutBand(image: Image.Image, values: np.ndarray, low: float, high: float) -> Image.Image:
    """
    The same erasure for pixel art, where there are no characters to blank.

    Cells outside the band become fully transparent. The mask is built at grid resolution
    and blown up with nearest-neighbour sampling, exactly as `convert2Pixel` does with the
    picture itself, so the holes line up with the blocks rather than straddling them.
    """
    keep = bandMask(values, low, high).astype(np.uint8) * 255
    mask = Image.fromarray(keep, 'L').resize(image.size, Image.Resampling.NEAREST)

    punched = image.convert('RGBA')
    punched.putalpha(mask)

    return punched


def gridToRows(chars: np.ndarray) -> list[str]:
    """Joins a 2D character grid into one string per row, which is what the writers expect."""
    return [''.join(row) for row in chars]


def flattenAlpha(image: Image.Image, background: int = 0) -> Image.Image:
    """
    Composites a transparent image onto a flat background.

    Without this, Pillow's conversion of an RGBA image ignores the alpha channel entirely
    and fully transparent pixels contribute whatever colour happens to sit underneath them.
    """
    if image.mode not in ('RGBA', 'LA', 'PA') and 'transparency' not in image.info:
        return image

    rgba = image.convert('RGBA')
    canvas = Image.new('RGBA', rgba.size, (background, background, background, 255))
    canvas.alpha_composite(rgba)

    return canvas.convert('RGB')


def convert2Pixel(image: Image.Image, imgSize: tuple[int, int], widthCount: int, heightCount: int) -> Image.Image:
    """
    Renders the image as pixel art: shrink to the tile grid, then blow it back up with
    nearest-neighbour sampling so each tile becomes a hard-edged block.
    """
    pValidateGrid(image.size, widthCount, heightCount)

    imgSmall = image.resize((widthCount, heightCount), Image.Resampling.BILINEAR)

    return imgSmall.resize(imgSize, Image.Resampling.NEAREST)


def pValidateGrid(imgSize: tuple[int, int], cols: int, rows: int) -> None:
    """
    --- Private method! ---\n
    Rejects grids that cannot be built, which would otherwise surface as a divide by zero
    when a tile ends up with no pixels in it.
    """
    width, height = imgSize
    if not 1 <= cols <= width:
        raise tools.Errors.VariableInvalidValueError('cols', cols, f"Tile count must be between 1 and {width}!")
    if not 1 <= rows <= height:
        raise tools.Errors.VariableInvalidValueError('rows', rows, f"Tile count must be between 1 and {height}!")


def pTileEdges(size: int, count: int) -> np.ndarray:
    """
    --- Private method! ---\n
    Pixel boundaries of `count` tiles across `size` pixels, rounded to integers.

    Rounding rather than truncating is what makes this match Pillow's BOX resampling, and
    matching it is what keeps the CPU and device paths in agreement.

    The rounding is deliberately half *up*, not numpy's default half to even. Pillow's BOX
    filter picks its boundary with `int(edge + 0.5)`, so a tile edge landing exactly on a
    half pixel goes to the higher pixel there. Using np.rint instead would send those few
    edges the other way and leave the two paths disagreeing on a stripe of cells.
    """
    return np.floor(np.arange(count + 1) * (size / count) + 0.5).astype(np.int64)


def pBlockMeanNumpy(pixels: np.ndarray, cols: int, rows: int) -> np.ndarray:
    """
    --- Private method! ---\n
    Block mean on the CPU, by summing each tile's rows and then its columns.

    `np.add.reduceat` sums the segments between the given boundaries in one C level pass,
    so this reduces straight to the tile grid without building anything image sized along
    the way. Each axis is divided by its own tile sizes, which is what lets the tiles have
    uneven widths without weighting the edges wrongly.
    """
    yEdges = pTileEdges(pixels.shape[0], rows)
    xEdges = pTileEdges(pixels.shape[1], cols)

    bands = np.add.reduceat(pixels, yEdges[:-1], axis = 0) / np.diff(yEdges)[:, None]

    return np.add.reduceat(bands, xEdges[:-1], axis = 1) / np.diff(xEdges)[None, :]


def pBlockMeanDevice(pixels, cols: int, rows: int, backend: ComputeBackend):
    """
    --- Private method! ---\n
    Block mean via cumulative sums, using only operations every backend provides.

    Each axis is reduced by taking a running total and subtracting it at the tile
    boundaries, which turns the whole grid into a handful of array operations.

    The vertical pass divides by the tile height before the horizontal pass runs. That
    ordering matters at float32: it keeps the running totals near 0-255 instead of letting
    them grow with the pixel count, which would start losing whole grayscale levels on
    large images.
    """
    height, width = pixels.shape

    yEdges = pTileEdges(height, rows)
    xEdges = pTileEdges(width, cols)

    deviceYEdges = backend.asarray(yEdges, 'int64')
    deviceXEdges = backend.asarray(xEdges, 'int64')
    tileHeights = backend.asarray(np.diff(yEdges))[:, None]
    tileWidths = backend.asarray(np.diff(xEdges))[None, :]

    columnTotals = backend.zeros((height + 1, width))
    columnTotals[1:] = backend.cumsum(pixels, axis = 0)
    bands = (columnTotals[deviceYEdges[1:]] - columnTotals[deviceYEdges[:-1]]) / tileHeights

    rowTotals = backend.zeros((rows, width + 1))
    rowTotals[:, 1:] = backend.cumsum(bands, axis = 1)

    return (rowTotals[:, deviceXEdges[1:]] - rowTotals[:, deviceXEdges[:-1]]) / tileWidths


def pSobel(pixels, backend: ComputeBackend):
    """
    --- Private method! ---\n
    Sobel gradients over the whole image, expressed as shifted slices rather than a
    convolution so that it needs nothing beyond indexing and arithmetic.

    The one pixel border is left at zero, which keeps the result the same shape as the
    input so it can be block-averaged on the same tile boundaries as the brightness grid.
    """
    height, width = pixels.shape

    topLeft, top, topRight = pixels[:-2, :-2], pixels[:-2, 1:-1], pixels[:-2, 2:]
    left, right = pixels[1:-1, :-2], pixels[1:-1, 2:]
    botLeft, bot, botRight = pixels[2:, :-2], pixels[2:, 1:-1], pixels[2:, 2:]

    gradX = backend.zeros((height, width))
    gradY = backend.zeros((height, width))

    gradX[1:-1, 1:-1] = (topRight + 2 * right + botRight) - (topLeft + 2 * left + botLeft)
    gradY[1:-1, 1:-1] = (botLeft + 2 * bot + botRight) - (topLeft + 2 * top + topRight)

    return gradX, gradY
