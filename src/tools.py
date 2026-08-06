###########################################################################
# Copyright (c) 2024-2026, Andy Pandy                                          #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################

import random
from enum import Enum
from math import isqrt
from typing import Iterator

APP_VERSION = "2.1.0"


class Errors:
    class GenericError(Exception):

        errorMsg = "Generic error message!"

        def __init__(self, error_msg = errorMsg, *args: object) -> None:
            self.errorMsg = error_msg

            super().__init__(self.errorMsg)

    class Unimplemented(GenericError):

        def __init__(self, *args: object) -> None:
            super().__init__("FUNCTION IS NOT IMPLEMENTED!")

    class VariableNotInitialisedError(GenericError):

        varName = ""
        errorMsg = "Value was accessed before being initialised!"

        def __init__(self, var_name: str, error_msg = errorMsg, *args: object) -> None:
            self.varName = var_name
            self.errorMsg = error_msg + f"\n\t\tVariable Name -> {var_name}"

            super().__init__(self.errorMsg)

    class VariableInvalidValueError(GenericError):

        varName = ""
        varValue = None
        errorMsg = "Variable has an invalid value!"

        def __init__(self, var_name: str, var_value, error_msg = errorMsg, *args: object) -> None:
            self.varName = var_name
            self.varValue = var_value
            self.errorMsg = error_msg + f"\n\t\tVariable Name -> {var_name}\n\t\tVariable Value -> {var_value}"

            super().__init__(self.errorMsg)


class ValidTypes(Enum):
    TXT = 0
    JPG = 1
    PNG = 2
    XML = 3
    SVG = 4
    GIF = 5
    MP4 = 6

    @classmethod
    def asList(cls) -> list[str]:
        return [v.name.lower() for v in cls]

    @classmethod
    def getImageTypes(cls) -> list[str]:
        return [v.name for v in cls if v.isImage()]

    @classmethod
    def getAnimatedTypes(cls) -> list[str]:
        return [v.name for v in cls if v.isAnimated()]

    @classmethod
    def fromExtension(cls, extension: str) -> 'ValidTypes':
        """Resolves '.png' or 'png' to the matching member. Raises VariableInvalidValueError if unknown."""
        name = extension.lstrip('.').upper()
        try:
            return cls[name]
        except KeyError:
            raise Errors.VariableInvalidValueError('extension', extension, "Unsupported output file type!")

    def isImage(self) -> bool:
        """True for raster formats, which are written by Pillow rather than as text."""
        return self in (ValidTypes.JPG, ValidTypes.PNG)

    def isAnimated(self) -> bool:
        """True for formats that hold a whole sequence of frames in one file."""
        return self in (ValidTypes.GIF, ValidTypes.MP4)

    def isText(self) -> bool:
        """True for formats written as text rather than by Pillow or a video encoder."""
        return not (self.isImage() or self.isAnimated())


# gray scale level values from:
# http://paulbourke.net/dataformats/asciiart/
# Ordered darkest -> lightest, so index 0 is the densest character.
GRAYSCALES = {
    10: '@%#*+=-:. ',
    70: "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\\|()1{}[]?-_+~<>i!lI;:,\"^`'. "
}

# Characters used by the edge detector, indexed by gradient direction bucket.
# The angle of the *gradient* is perpendicular to the edge it describes, so each
# bucket maps to the character that draws the edge, not the gradient.
EDGE_CHARS = ('|', '/', '-', '\\')


class CharSet:
    """
    A named way of turning brightness into characters.

    Two kinds live behind one name. A *ramp* set picks one character per cell from a
    string ordered densest first, which is what the tool has always done. A *sub-cell*
    set splits each cell into a small grid of dots, decides each dot independently, and
    packs the result into a single character, which buys several times the resolution
    out of the same number of cells.
    """

    def __init__(self, name: str, ramp: str | None = None,
                 subShape: tuple[int, int] | None = None,
                 bitWeights: tuple[tuple[int, ...], ...] | None = None,
                 baseCodePoint: int = 0, lookup: str | None = None,
                 needsColor: bool = False, description: str = '') -> None:
        self.name = name
        self.ramp = ramp
        self.subShape = subShape                # (dotRows, dotCols) per character cell
        self.bitWeights = bitWeights            # weight of each dot, same shape as subShape
        self.baseCodePoint = baseCodePoint      # characters are baseCodePoint + packed bits
        self.lookup = lookup                    # ...unless an explicit lookup string is given
        self.needsColor = needsColor
        self.description = description

    @property
    def isSubCell(self) -> bool:
        return self.subShape is not None

    def characterFor(self, packedBits: int) -> str:
        """The character representing one cell's worth of packed dots."""
        if self.lookup is not None:
            return self.lookup[packedBits]

        return chr(self.baseCodePoint + packedBits)

    @property
    def blank(self) -> str:
        """
        The character for a cell that has been removed entirely, as the band threshold does.

        A plain space would do for a ramp set, but not for a sub-cell one: braille cells are
        drawn from U+2800 upwards, and mixing an ordinary space into that run leaves a gap of
        a different width wherever a cell was dropped. Every sub-cell set has a character
        with no dots lit, which is the right kind of nothing.
        """
        if self.isSubCell:
            return self.characterFor(0)

        return ' '


# Braille dot numbering is not in reading order: dots 1-6 fill the top three rows in
# columns, and dots 7-8 were added underneath later, which is why the last row's weights
# jump to 0x40 and 0x80. Layout is documented at https://en.wikipedia.org/wiki/Braille_Patterns
BRAILLE_BITS = ((0x01, 0x08),
                (0x02, 0x10),
                (0x04, 0x20),
                (0x40, 0x80))

# The 16 quadrant block characters, indexed by the same bit order as QUADRANT_BITS below.
QUADRANT_CHARS = ' ▘▝▀▖▌▞▛▗▚▐▜▄▙▟█'
QUADRANT_BITS = ((1, 2),
                 (4, 8))

# Upper half block over a background, so one character shows two stacked pixels in colour.
HALFBLOCK_CHARS = ' ▀▄█'
HALFBLOCK_BITS = ((1,),
                  (2,))

CHARSETS = {
    'ascii70'   : CharSet('ascii70', ramp = GRAYSCALES[70],
                          description = 'the default 70 character ASCII ramp'),
    'ascii10'   : CharSet('ascii10', ramp = GRAYSCALES[10],
                          description = 'a short 10 character ASCII ramp'),
    'blocks'    : CharSet('blocks', ramp = '█▓▒░ ',
                          description = 'Unicode block shading, densest first'),
    'shades'    : CharSet('shades', ramp = '█▉▊▋▌▍▎▏ ',
                          description = 'Unicode partial blocks, a longer shading ramp'),
    'braille'   : CharSet('braille', subShape = (4, 2), bitWeights = BRAILLE_BITS,
                          baseCodePoint = 0x2800,
                          description = 'braille dots, 2x4 per cell, 8x the resolution'),
    'quadrants' : CharSet('quadrants', subShape = (2, 2), bitWeights = QUADRANT_BITS,
                          lookup = QUADRANT_CHARS,
                          description = 'quadrant blocks, 2x2 per cell, 4x the resolution'),
    'halfblocks': CharSet('halfblocks', subShape = (2, 1), bitWeights = HALFBLOCK_BITS,
                          lookup = HALFBLOCK_CHARS, needsColor = True,
                          description = 'half blocks, 2x the vertical resolution, best with -c'),
}

DEFAULT_CHARSET = 'ascii70'

# 8x8 Bayer matrix for ordered dithering. Values are the order in which dots switch on as
# an area darkens, so tiling this across the image and comparing against it turns a flat
# tone into an even pattern instead of a hard edge.
BAYER_MATRIX = (
    ( 0, 32,  8, 40,  2, 34, 10, 42),
    (48, 16, 56, 24, 50, 18, 58, 26),
    (12, 44,  4, 36, 14, 46,  6, 38),
    (60, 28, 52, 20, 62, 30, 54, 22),
    ( 3, 35, 11, 43,  1, 33,  9, 41),
    (51, 19, 59, 27, 49, 17, 57, 25),
    (15, 47,  7, 39, 13, 45,  5, 37),
    (63, 31, 55, 23, 61, 29, 53, 21),
)

# A monospace cell is roughly twice as tall as it is wide. Courier sits at about
# 0.43; 0.5 is a good neutral default across terminals and the bundled fonts.
DEFAULT_CHAR_ASPECT = 0.5

# Map taken from https://rabbit.eng.miami.edu/info/htmlchars.html
# Applies to any XML-family output, so both the SVG and the XML writers use it.
MARKUP_ESCAPES = {
    '&' : '&amp;',
    '<' : '&lt;',
    '>' : '&gt;',
}

# Word pools for generated output file names. Grouped by the kind of adjective so that a
# generated name draws from two different groups.
NAME_ADJECTIVES = (
    ('Cheap', 'Expensive', 'Nice', 'Ugly', 'Stupid', 'Smart', 'Brilliant', 'Great', 'Pretty', 'Rich'),
    ('Small', 'Tiny', 'Huge', 'Big', 'Miniscule', 'Tall', 'Little', 'Large', 'Colossal', 'Puny'),
    ('Old', 'New', 'Ancient', 'Teen', 'Young', 'Antique', 'Elderly', 'Aged', 'Mature', 'Childish'),
    ('Round', 'Square', 'Angled', 'Convex', 'Oblique', 'Straight', 'Thick', 'Curved', 'Wide', 'Wavy'),
    ('Red', 'Green', 'Cyan', 'Glossy', 'Vibrant', 'Black', 'Grey', 'White', 'Purple', 'Blue'),
    ('Greek', 'French', 'Spanish', 'Italian', 'English', 'Swedish', 'German', 'Japanese', 'Korean', 'Indian'),
    ('Wooden', 'Steel', 'Natural', 'Synthetic', 'Plastic', 'Gold', 'Ceramic', 'Marble', 'Smooth', 'Soft'),
)
NAME_OBJECTS = (
    'Table', 'House', 'Raindrop', 'Car', 'JetEngine', 'Bottle', 'Phone', 'Electron', 'Tree', 'Cat',
    'Parrot', 'Candle', 'Coin', 'Bed', 'Printer', 'Leaf', 'Sponge', 'Kettle',
)


def pDivisorGenerator(n: int) -> Iterator[int]:
    """
    --- Private method! ---\n
    Yields every divisor of n in ascending order, testing only up to sqrt(n).
    """
    if n < 1:
        raise Errors.VariableInvalidValueError('n', n, "Cannot find the divisors of a non-positive number!")

    upperHalf = []
    for i in range(1, isqrt(n) + 1):
        if n % i:
            continue
        yield i
        if i != n // i:
            upperHalf.append(n // i)

    yield from reversed(upperHalf)


def pGetDivisors(n: int) -> list[int]:
    return list(pDivisorGenerator(n))


def pGetUniqueName() -> str:
    """
    --- Private method! ---\n
    Builds a readable random name in the form 'Adjective_Adjective_Object'.

    Two adjectives are drawn from different groups, so the result reads like a description
    rather than pairing two words that mean the same sort of thing.
    """
    firstGroup, secondGroup = random.sample(NAME_ADJECTIVES, 2)

    return f"{random.choice(firstGroup)}_{random.choice(secondGroup)}_{random.choice(NAME_OBJECTS)}"


def pColorsToHex(r: int = 0, g: int = 0, b: int = 0) -> str:
    if not (0 <= r <= 255):
        raise Errors.VariableInvalidValueError('r', r, "RGB values must be between 0 and 255 (inclusive)!")
    if not (0 <= g <= 255):
        raise Errors.VariableInvalidValueError('g', g, "RGB values must be between 0 and 255 (inclusive)!")
    if not (0 <= b <= 255):
        raise Errors.VariableInvalidValueError('b', b, "RGB values must be between 0 and 255 (inclusive)!")

    return f"#{r:02x}{g:02x}{b:02x}"


def pEscapeMarkup(char: str) -> str:
    """
    --- Private method! ---\n
    Escapes a character that would otherwise break XML-family output.
    """
    # Gets key, or defaults to returning the character
    return MARKUP_ESCAPES.get(char, char)


def pEscapeMarkupText(text: str) -> str:
    """
    --- Private method! ---\n
    Escapes a whole string for XML-family output.
    """
    return ''.join(MARKUP_ESCAPES.get(c, c) for c in text)
