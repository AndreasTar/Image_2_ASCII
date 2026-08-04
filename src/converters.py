###########################################################################
# Copyright (c) 2024, Andy Pandy                                          #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################

"""
Writers for every output format.

They all take the same `Conversion`: a 2D grid of characters, and optionally a matching
grid of RGB colours. Holding the result as a 2D grid rather than a flat list is what keeps
the colour of a cell attached to the cell it belongs to, no matter how the grid is shaped.
"""

import numpy as np
import svg
from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFont

from src import tools

# Rendering metrics for the raster and SVG writers.
FONT_SIZE = 14
SVG_CELL_WIDTH = 8
SVG_LINE_HEIGHT = 18
SVG_PADDING = 4

# Fonts to try, best looking first. Alignment does not depend on finding a monospace face,
# since glyphs are placed cell by cell either way, but one looks considerably better.
#
# Coverage is the real constraint. Most fixed width fonts, Consolas and Courier New
# included, have no braille or quadrant block glyphs at all, and asking for a character a
# font does not have gets a .notdef box rather than an error. The symbol fonts listed
# afterwards do carry those ranges, so a run using them falls through to one of those.
MONOSPACE_CANDIDATES = (
    'DejaVuSansMono.ttf',                                           # covers braille, common on Linux
    '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',
    '/usr/share/fonts/TTF/DejaVuSansMono.ttf',
    'consola.ttf',                                                  # Windows, no braille
    '/System/Library/Fonts/Menlo.ttc',                              # macOS
    '/Library/Fonts/Courier New.ttf',
    'cour.ttf',
)

SYMBOL_CANDIDATES = (
    'seguisym.ttf',                                                 # Segoe UI Symbol, Windows
    'DejaVuSans.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    'unifont.ttf',
    '/System/Library/Fonts/Apple Symbols.ttf',
    'arialuni.ttf',
)

# Codepoint that no font assigns, so whatever it renders as is that font's "missing glyph"
# mark. Anything rendering identically to it is missing too.
UNASSIGNED_CODEPOINT = '￿'

# The block characters are exact rectangles by definition, and they are meant to tile with
# no seam between them. Left to a font they do not: the glyph fills the em box while the
# cell is the full ascent plus descent, so every row ends up separated by a stripe of
# background. Drawing them as the rectangles they are fixes that, makes the result
# identical on every machine, and means these sets need no symbol font installed at all.
#
# Each entry is a list of (left, top, right, bottom) rectangles in fractions of the cell.
BLOCK_GEOMETRY = {
    ' ': [],
    '█': [(0.0, 0.0, 1.0, 1.0)],
    '▀': [(0.0, 0.0, 1.0, 0.5)],
    '▄': [(0.0, 0.5, 1.0, 1.0)],
    '▌': [(0.0, 0.0, 0.5, 1.0)],
    '▐': [(0.5, 0.0, 1.0, 1.0)],
    '▘': [(0.0, 0.0, 0.5, 0.5)],
    '▝': [(0.5, 0.0, 1.0, 0.5)],
    '▖': [(0.0, 0.5, 0.5, 1.0)],
    '▗': [(0.5, 0.5, 1.0, 1.0)],
    '▚': [(0.0, 0.0, 0.5, 0.5), (0.5, 0.5, 1.0, 1.0)],
    '▞': [(0.5, 0.0, 1.0, 0.5), (0.0, 0.5, 0.5, 1.0)],
    '▛': [(0.0, 0.0, 1.0, 0.5), (0.0, 0.5, 0.5, 1.0)],
    '▜': [(0.0, 0.0, 1.0, 0.5), (0.5, 0.5, 1.0, 1.0)],
    '▙': [(0.0, 0.0, 0.5, 0.5), (0.0, 0.5, 1.0, 1.0)],
    '▟': [(0.5, 0.0, 1.0, 0.5), (0.0, 0.5, 1.0, 1.0)],
    '▏': [(0.0, 0.0, 0.125, 1.0)],
    '▎': [(0.0, 0.0, 0.25, 1.0)],
    '▍': [(0.0, 0.0, 0.375, 1.0)],
    '▋': [(0.0, 0.0, 0.625, 1.0)],
    '▊': [(0.0, 0.0, 0.75, 1.0)],
    '▉': [(0.0, 0.0, 0.875, 1.0)],
}

# The shading characters are a proportion of coverage rather than a shape, so they are
# drawn as an even pattern at that density.
SHADE_DENSITY = {'░': 0.25, '▒': 0.5, '▓': 0.75}

FOREGROUND_ON_LIGHT = (17, 17, 17)
BACKGROUND_LIGHT = (238, 238, 238)
BACKGROUND_DARK = (17, 17, 17)

# Renderers collapse runs of whitespace, which would pull a row out of alignment. A
# non breaking space occupies the same cell in a fixed width font and is left alone.
NBSP = ' '

# Width of one cell in the coloured text format: six hex digits plus the character. Cells
# are separated by a space, but the character itself can be a space, so anything reading
# this format has to work in fixed steps rather than splitting on the separator.
COLORED_TEXT_CELL_WIDTH = 7

# ANSI control sequences, used for coloured terminal output and animation playback.
ANSI_ESCAPE = '\x1b'
ANSI_RESET = '\x1b[0m'
ANSI_CLEAR_SCREEN = '\x1b[2J\x1b[H'
ANSI_HIDE_CURSOR = '\x1b[?25l'
ANSI_SHOW_CURSOR = '\x1b[?25h'

# Precomputed two digit hex, so colour grids can be formatted without a Python loop.
pHexByte = np.array([f'{i:02x}' for i in range(256)])

# Fonts are resolved by probing glyph coverage, which is far too slow to repeat for every
# frame of an animation, so the answer is kept per set of characters needed.
pFontCache: dict = {}


@dataclass
class Conversion:
    """
    The finished conversion: what character sits in each cell, and optionally what colour.

    `colors` is None for a grayscale run. When present it is a (rows, cols, 3) uint8 array
    lined up cell for cell with `chars`.

    `backgrounds` is the same shape again, and is only set by character sets that put two
    colours in one cell, such as halfblocks. Writers that cannot express a per-cell
    background, meaning the plain text and XML ones, ignore it.
    """

    chars: np.ndarray
    colors: np.ndarray | None = None
    backgrounds: np.ndarray | None = None
    durationMs: float = 0.0

    @property
    def rows(self) -> int:
        return self.chars.shape[0]

    @property
    def cols(self) -> int:
        return self.chars.shape[1]

    @property
    def isColored(self) -> bool:
        return self.colors is not None

    @property
    def hasBackgrounds(self) -> bool:
        return self.backgrounds is not None

    def asRows(self) -> list[str]:
        """One string per row of the grid."""
        return [''.join(row) for row in self.chars]

    def asHexGrid(self, prefix: str = '#') -> np.ndarray | None:
        """The colour grid as hex strings, or None when the run is not coloured."""
        if self.colors is None:
            return None

        red, green, blue = self.colors[..., 0], self.colors[..., 1], self.colors[..., 2]
        packed = np.char.add(np.char.add(pHexByte[red], pHexByte[green]), pHexByte[blue])

        return np.char.add(prefix, packed) if prefix else packed


def convertToText(conversion: Conversion, withColor: bool = False) -> list[str]:
    """
    Plain text output, one line per row.

    With `withColor` each cell becomes 'RRGGBBc', which keeps the colour information in a
    format that is still a text file.
    """
    if not withColor or not conversion.isColored:
        return conversion.asRows()

    cells = np.char.add(np.char.upper(conversion.asHexGrid(prefix = '')), conversion.chars)

    return [' '.join(row) for row in cells]


def convertToAnsi(conversion: Conversion) -> list[str]:
    """
    Terminal output with 24-bit colour escape sequences, one string per row.

    Runs of identical colour share a single escape sequence. Without that a coloured row
    carries about twenty bytes of escape per character, which is slow to write and slower
    still to redraw every frame during animation playback.

    Falls back to plain characters when the conversion has no colour, so this is always
    safe to call.
    """
    if not conversion.isColored:
        return conversion.asRows()

    foreground = conversion.colors
    background = conversion.backgrounds
    lines = []

    for row in range(conversion.rows):
        parts = []
        lastForeground = lastBackground = None

        for col in range(conversion.cols):
            colour = tuple(int(v) for v in foreground[row, col])
            if colour != lastForeground:
                parts.append(f"{ANSI_ESCAPE}[38;2;{colour[0]};{colour[1]};{colour[2]}m")
                lastForeground = colour

            if background is not None:
                behind = tuple(int(v) for v in background[row, col])
                if behind != lastBackground:
                    parts.append(f"{ANSI_ESCAPE}[48;2;{behind[0]};{behind[1]};{behind[2]}m")
                    lastBackground = behind

            parts.append(str(conversion.chars[row, col]))

        parts.append(ANSI_RESET)
        lines.append(''.join(parts))

    return lines


def convertToXML(conversion: Conversion, withColor: bool = False) -> list[str]:
    """
    XML output, as a list of lines.

    A grayscale row is written as a single element holding the whole row, which keeps the
    file to a sane size. A coloured row needs one element per cell to carry the colour.
    Every character goes through escaping, which matters because the default 70 character
    ramp contains '&', '<' and '>'.
    """
    colored = withColor and conversion.isColored

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             f'<ascii rows="{conversion.rows}" cols="{conversion.cols}" colored="{str(colored).lower()}">']

    if colored:
        hexGrid = conversion.asHexGrid()
        for index, (charRow, colorRow) in enumerate(zip(conversion.chars, hexGrid)):
            cells = ''.join(f'<c f="{color}">{tools.pEscapeMarkup(char)}</c>'
                            for char, color in zip(charRow, colorRow))
            lines.append(f'\t<row index="{index}">{cells}</row>')
    else:
        for index, row in enumerate(conversion.asRows()):
            lines.append(f'\t<row index="{index}">{tools.pEscapeMarkupText(row)}</row>')

    lines.append('</ascii>')

    return lines


def convertToSVG(conversion: Conversion) -> svg.SVG:
    """
    SVG output.

    Runs of cells sharing a colour become a single <tspan> with an explicit x and a
    textLength, which pins the run to the character grid without needing one element per
    character. A grayscale row is one run, so a grayscale image is one element per row.
    """
    width = conversion.cols * SVG_CELL_WIDTH
    height = conversion.rows * SVG_LINE_HEIGHT
    colored = conversion.isColored

    hexGrid = conversion.asHexGrid()
    foreground = tools.pColorsToHex(*FOREGROUND_ON_LIGHT)

    # Cells that carry their own background need a rectangle drawn behind them, since SVG
    # text has no background of its own. Runs of one colour become one rectangle.
    cellRects: list[svg.Element] = []
    if conversion.hasBackgrounds:
        behindGrid = Conversion(conversion.chars, conversion.backgrounds).asHexGrid()
        for rowIndex in range(conversion.rows):
            for startCol, endCol in pColorRuns(behindGrid[rowIndex], conversion.cols):
                cellRects.append(svg.Rect(
                    x = SVG_PADDING + startCol * SVG_CELL_WIDTH,
                    y = SVG_PADDING + rowIndex * SVG_LINE_HEIGHT,
                    width = (endCol - startCol) * SVG_CELL_WIDTH,
                    height = SVG_LINE_HEIGHT,
                    fill = behindGrid[rowIndex][startCol],
                ))

    spans: list[svg.Element] = []
    for rowIndex, charRow in enumerate(conversion.chars):
        baseline = (rowIndex + 1) * SVG_LINE_HEIGHT
        colorRow = hexGrid[rowIndex] if colored else None

        for startCol, endCol in pColorRuns(colorRow, conversion.cols):
            text = ''.join(charRow[startCol:endCol])
            if not text.strip():
                # A run of nothing but spaces draws nothing, so skip the element entirely.
                continue

            spans.append(svg.TSpan(
                x = SVG_PADDING + startCol * SVG_CELL_WIDTH,
                y = baseline,
                fill = colorRow[startCol] if colored else foreground,
                text = tools.pEscapeMarkupText(text).replace(' ', NBSP),
                textLength = (endCol - startCol) * SVG_CELL_WIDTH,
            ))

    elements = [
        svg.Style(text = f"text {{ font-family: monospace; font-size: {FONT_SIZE}px; white-space: pre; }}"),
        svg.Rect(x = 0, y = 0, width = width + SVG_PADDING * 2, height = height + SVG_PADDING * 2,
                 rx = 9, fill = tools.pColorsToHex(*(BACKGROUND_DARK if colored else BACKGROUND_LIGHT))),
        *cellRects,
        svg.Text(elements = spans),
    ]

    return svg.SVG(
        width = width + SVG_PADDING * 2,
        height = height + SVG_PADDING * 2,
        elements = elements,
    )


def convertToIMG(conversion: Conversion) -> Image.Image:
    """
    Raster output.

    Every distinct character is rendered once into a glyph atlas, and the picture is then
    assembled by indexing that atlas with the character grid. That turns what would be one
    draw call per cell into a couple of array operations, which is roughly an order of
    magnitude quicker on a large grid.
    """
    colored = conversion.isColored

    uniqueChars, lookup = np.unique(conversion.chars, return_inverse = True)
    # The font is chosen from what this conversion actually draws, so a braille run gets a
    # font with braille in it rather than whichever fixed width face happened to load.
    font, cellWidth, cellHeight = pLoadFont(''.join(str(char) for char in uniqueChars))

    atlas = np.stack([pRenderGlyph(char, font, cellWidth, cellHeight) for char in uniqueChars])

    # (rows, cols, cellHeight, cellWidth) -> one flat coverage mask for the whole picture.
    tiles = atlas[lookup.reshape(conversion.chars.shape)]
    mask = tiles.transpose(0, 2, 1, 3).reshape(conversion.rows * cellHeight, conversion.cols * cellWidth)

    size = (conversion.cols * cellWidth, conversion.rows * cellHeight)

    if not colored:
        image = Image.new('RGB', size, BACKGROUND_LIGHT)
        image.paste(FOREGROUND_ON_LIGHT, (0, 0), Image.fromarray(mask, 'L'))
        return image

    # Blend each glyph's coverage against its cell colour. Broadcasting the small colour
    # grid up to full resolution avoids materialising a repeated copy of it.
    coverage = mask[..., None].astype(np.uint16)
    cellColors = pExpandToPixels(conversion.colors, cellWidth, cellHeight, size)

    if conversion.hasBackgrounds:
        behind = pExpandToPixels(conversion.backgrounds, cellWidth, cellHeight, size)
    else:
        behind = np.array(BACKGROUND_DARK, dtype = np.uint16)

    blended = (cellColors * coverage + behind * (255 - coverage)) // 255

    return Image.fromarray(blended.astype(np.uint8), 'RGB')


def pExpandToPixels(grid: np.ndarray, cellWidth: int, cellHeight: int,
                    size: tuple[int, int]) -> np.ndarray:
    """
    --- Private method! ---\n
    Blows a per-cell colour grid up to one value per pixel.

    Broadcasting first and reshaping once is markedly quicker than repeating the array
    along each axis in turn, which would build a full sized copy twice over.
    """
    rows, cols = grid.shape[:2]

    return np.broadcast_to(
        grid[:, None, :, None, :], (rows, cellHeight, cols, cellWidth, 3)
    ).reshape(size[1], size[0], 3).astype(np.uint16)


def convertToAnimatedGIF(conversions: list[Conversion], defaultDurationMs: float = 100.0) -> tuple:
    """
    Renders every frame and returns what Pillow needs to write an animated GIF.

    Returns (firstFrame, remainingFrames, durations). Pillow wants the animation split
    that way: the first frame is the object saved, the rest are passed to it.
    """
    if not conversions:
        raise tools.Errors.GenericError("There are no frames to write!")

    images = [convertToIMG(conversion) for conversion in conversions]
    durations = [int(conversion.durationMs or defaultDurationMs) for conversion in conversions]

    return images[0], images[1:], durations


def convertFramesToImages(conversions: list[Conversion]) -> list[Image.Image]:
    """Renders every frame to a picture, for handing to a video encoder."""
    return [convertToIMG(conversion) for conversion in conversions]


def pColorRuns(colorRow: np.ndarray | None, cols: int):
    """
    --- Private method! ---\n
    Yields (start, end) spans of cells that share a colour. A grayscale row is one span.
    """
    if colorRow is None:
        yield 0, cols
        return

    start = 0
    for col in range(1, cols):
        if colorRow[col] != colorRow[start]:
            yield start, col
            start = col

    yield start, cols


def pLoadFont(requiredChars: str | None = None) -> tuple[ImageFont.FreeTypeFont, int, int]:
    """
    --- Private method! ---\n
    Loads a font that can actually draw `requiredChars`, and sizes the cell from its metrics.

    Coverage is checked rather than assumed. Asking a font for a character it does not
    have returns a .notdef box, not an error, so a braille render in Consolas comes out as
    a neat grid of empty rectangles that looks deliberate until you look closely. Fonts
    are tried in order and the first one that covers every character in use wins.
    """
    required = set(requiredChars or (tools.GRAYSCALES[70] + ''.join(tools.EDGE_CHARS)))
    # Block characters never reach the font, so they must not influence which one is
    # picked or how wide a cell it gets.
    required -= set(BLOCK_GEOMETRY) | set(SHADE_DENSITY)
    required = required or {'M'}

    cacheKey = frozenset(required)
    if cacheKey in pFontCache:
        return pFontCache[cacheKey]

    fallback = None
    for candidate in MONOSPACE_CANDIDATES + SYMBOL_CANDIDATES:
        try:
            font = ImageFont.truetype(candidate, FONT_SIZE)
        except OSError:
            continue

        fallback = fallback or font
        if pCoversAll(font, required):
            result = pMeasureCell(font, required)
            pFontCache[cacheKey] = result
            return result

    if fallback is None:
        fallback = ImageFont.load_default(size = FONT_SIZE)

    missing = ''.join(sorted(char for char in required if not pCoversAll(fallback, {char})))
    if missing:
        print(f"\nWarning: no installed font could be found with glyphs for: {missing!r}\n"
              f"\tThose cells will render as empty boxes in image output. Text output is unaffected.\n")

    result = pMeasureCell(fallback, required)
    pFontCache[cacheKey] = result

    return result


def pMeasureCell(font: ImageFont.FreeTypeFont, required: set) -> tuple[ImageFont.FreeTypeFont, int, int]:
    """
    --- Private method! ---\n
    Works out the cell size from the font's own metrics and the characters being drawn,
    so glyphs are neither clipped nor left swimming in an oversized cell.
    """
    ascent, descent = font.getmetrics()
    cellWidth = max(int(round(font.getlength(char))) for char in required)

    return font, max(cellWidth, 1), max(ascent + descent, 1)


def pCoversAll(font: ImageFont.FreeTypeFont, chars: set) -> bool:
    """
    --- Private method! ---\n
    Whether the font has a real glyph for every one of these characters.

    Compares each rendering against the font's own missing-glyph mark, which is the only
    way to tell without reading the font tables and taking on a dependency to do it.

    Drawing nothing is deliberately *not* treated as missing. U+2800, the blank braille
    cell, is a real glyph that renders as nothing at all, and rejecting fonts over it
    would rule out every font that can actually draw braille.
    """
    notdef = pRenderProbe(font, UNASSIGNED_CODEPOINT)

    if np.array_equal(notdef, pRenderProbe(font, ' ')):
        # This font draws nothing for an unassigned codepoint, so there is no mark to
        # recognise a missing glyph by. Assume it copes rather than rejecting it blindly.
        return True

    for char in chars:
        if np.array_equal(pRenderProbe(font, char), notdef):
            return False

    return True


def pRenderProbe(font: ImageFont.FreeTypeFont, char: str) -> np.ndarray:
    """
    --- Private method! ---\n
    Draws one character into a small buffer, for comparing glyphs against each other.
    """
    probe = Image.new('L', (FONT_SIZE * 3, FONT_SIZE * 3), 0)
    ImageDraw.Draw(probe).text((2, 2), char, 255, font = font)

    return np.asarray(probe)


def pRenderGlyph(char: str, font: ImageFont.FreeTypeFont, cellWidth: int, cellHeight: int) -> np.ndarray:
    """
    --- Private method! ---\n
    Draws one character into a cell sized coverage mask, centred horizontally.

    Block characters are drawn geometrically rather than from the font, so they tile
    without seams. Everything else goes through the font as normal.
    """
    character = str(char)

    if character in BLOCK_GEOMETRY or character in SHADE_DENSITY:
        return pRenderBlockGlyph(character, cellWidth, cellHeight)

    glyph = Image.new('L', (cellWidth, cellHeight), 0)
    offset = max(0, (cellWidth - int(round(font.getlength(character)))) // 2)
    ImageDraw.Draw(glyph).text((offset, 0), character, 255, font = font)

    return np.asarray(glyph)


def pRenderBlockGlyph(char: str, cellWidth: int, cellHeight: int) -> np.ndarray:
    """
    --- Private method! ---\n
    Draws a block or shading character as the exact shape it is defined to be.
    """
    if char in SHADE_DENSITY:
        # An ordered pattern at the right density, which tiles evenly across neighbouring
        # cells instead of showing where one glyph stops and the next begins.
        rows = np.arange(cellHeight)[:, None]
        cols = np.arange(cellWidth)[None, :]
        pattern = ((rows * 2 + cols * 3) % 4) / 4.0

        return np.where(pattern < SHADE_DENSITY[char], 255, 0).astype(np.uint8)

    mask = np.zeros((cellHeight, cellWidth), dtype = np.uint8)
    for left, top, right, bottom in BLOCK_GEOMETRY[char]:
        mask[int(round(top * cellHeight)):int(round(bottom * cellHeight)),
             int(round(left * cellWidth)):int(round(right * cellWidth))] = 255

    return mask
