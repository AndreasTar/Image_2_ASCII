###########################################################################
# Copyright (c) 2024, Andy Pandy                                          #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################

"""
The named character sets, especially the ones that pack several dots into one character.
"""

import numpy as np
import pytest
from PIL import Image

from src import backend, compute, converters, tools

SUB_CELL_SETS = [name for name, charSet in tools.CHARSETS.items() if charSet.isSubCell]
RAMP_SETS = [name for name, charSet in tools.CHARSETS.items() if not charSet.isSubCell]


@pytest.fixture(scope = 'module')
def cpu():
    return compute.getCpuBackend()


def solidImage(value: int, size: tuple[int, int] = (64, 64)) -> Image.Image:
    return Image.new('L', size, value)


def halfDarkImage(size: tuple[int, int] = (64, 64)) -> Image.Image:
    """Left half black, right half white."""
    pixels = np.zeros((size[1], size[0]), dtype = np.uint8)
    pixels[:, size[0] // 2:] = 255

    return Image.fromarray(pixels, 'L')


# ================= Definitions ================

def testEveryCharsetIsUsable():
    for name, charSet in tools.CHARSETS.items():
        assert charSet.name == name
        assert charSet.description
        assert charSet.isSubCell or charSet.ramp, f"{name} is neither a ramp nor sub-cell"


@pytest.mark.parametrize('name', SUB_CELL_SETS)
def testSubCellWeightsMatchTheirShape(name):
    charSet = tools.CHARSETS[name]
    weights = np.array(charSet.bitWeights)

    assert weights.shape == charSet.subShape
    assert len(set(weights.flatten())) == weights.size, "each dot needs its own bit"
    assert sorted(weights.flatten()) == [2 ** i for i in range(weights.size)], "weights must be distinct bits"


@pytest.mark.parametrize('name', SUB_CELL_SETS)
def testEveryBitPatternHasACharacter(name):
    """Packing is only safe if every combination of dots maps to something."""
    charSet = tools.CHARSETS[name]
    total = int(np.array(charSet.bitWeights).sum())

    for value in range(total + 1):
        character = charSet.characterFor(value)
        assert isinstance(character, str) and len(character) == 1


def testBrailleUsesTheStandardDotNumbering():
    """
    Braille dot weights are not in reading order, and getting them wrong silently produces
    plausible looking nonsense, so the layout is pinned here.
    """
    assert tools.BRAILLE_BITS == ((0x01, 0x08), (0x02, 0x10), (0x04, 0x20), (0x40, 0x80))
    assert tools.CHARSETS['braille'].characterFor(0) == '⠀'
    assert tools.CHARSETS['braille'].characterFor(0xFF) == '⣿'
    assert tools.CHARSETS['braille'].characterFor(0x01) == '⠁'


def testQuadrantLookupIsInBitOrder():
    charSet = tools.CHARSETS['quadrants']

    assert charSet.characterFor(0) == ' '
    assert charSet.characterFor(15) == '█'
    assert charSet.characterFor(1) == '▘', "bit 1 is the top left quadrant"
    assert charSet.characterFor(2) == '▝', "bit 2 is the top right quadrant"
    assert charSet.characterFor(3) == '▀', "top left plus top right is the upper half"


# ================= Rendering ================

@pytest.mark.parametrize('name', SUB_CELL_SETS)
def testSubCellGridHasTheRequestedShape(grayImage, cpu, name):
    grid = backend.toSubCellGrid(grayImage, 20, 12, tools.CHARSETS[name], cpu)

    assert grid.shape == (12, 20)


@pytest.mark.parametrize('name', SUB_CELL_SETS)
def testDarkIsInk(cpu, name):
    """
    A dot goes on where the image is dark, matching the ramps where index 0 is densest.
    Inking the bright side instead renders a photograph as its own negative, which is what
    the first version of this did.
    """
    charSet = tools.CHARSETS[name]
    grid = backend.toSubCellGrid(halfDarkImage(), 8, 8, charSet, cpu)

    darkSide = set(grid[:, :4].flatten())
    brightSide = set(grid[:, 4:].flatten())

    empty = charSet.characterFor(0)
    full = charSet.characterFor(int(np.array(charSet.bitWeights).sum()))

    assert darkSide == {full}, "the dark half should be fully inked"
    assert brightSide == {empty}, "the bright half should be blank"


@pytest.mark.parametrize('name', SUB_CELL_SETS)
def testInvertSwapsWhichSideIsInked(cpu, name):
    charSet = tools.CHARSETS[name]
    plain = backend.toSubCellGrid(halfDarkImage(), 8, 8, charSet, cpu)
    inverted = backend.toSubCellGrid(halfDarkImage(), 8, 8, charSet, cpu, invert = True)

    assert set(plain[:, :4].flatten()) == set(inverted[:, 4:].flatten())
    assert set(plain[:, 4:].flatten()) == set(inverted[:, :4].flatten())


@pytest.mark.parametrize('name', SUB_CELL_SETS)
def testExplicitThresholdIsHonoured(cpu, name):
    """A threshold above everything inks the lot; below everything inks nothing."""
    charSet = tools.CHARSETS[name]
    image = solidImage(120)

    allOn = backend.toSubCellGrid(image, 6, 6, charSet, cpu, threshold = 255)
    allOff = backend.toSubCellGrid(image, 6, 6, charSet, cpu, threshold = 0)

    full = charSet.characterFor(int(np.array(charSet.bitWeights).sum()))
    assert set(allOn.flatten()) == {full}
    assert set(allOff.flatten()) == {charSet.characterFor(0)}


def testDitheringCarriesTone(cpu):
    """
    On a gradient, dithering should give many more distinct dot patterns than one hard
    cutoff, because that is the whole point of it: representing a tone by dot density
    rather than snapping every cell to full or empty.

    Note a perfectly flat tone is expected to dither to one repeating pattern. That is
    correct, not a failure: an even tone gets an even pattern.
    """
    charSet = tools.CHARSETS['braille']
    ramp = np.tile(np.linspace(0, 255, 128, dtype = np.uint8), (128, 1))
    image = Image.fromarray(ramp, 'L')

    plain = backend.toSubCellGrid(image, 16, 16, charSet, cpu)
    dithered = backend.toSubCellGrid(image, 16, 16, charSet, cpu, dither = True)

    assert len(set(dithered.flatten())) > len(set(plain.flatten()))


def testDitheringDensityTracksBrightness(cpu):
    """A darker flat tone must come back with more dots switched on than a lighter one."""
    charSet = tools.CHARSETS['braille']

    def inkedFraction(value: int) -> float:
        grid = backend.toSubCellGrid(solidImage(value), 16, 16, charSet, cpu, dither = True)
        # Count the set bits in each cell to get the dot density.
        return sum(bin(ord(char) - 0x2800).count('1') for char in grid.flatten()) / (grid.size * 8)

    dark, mid, light = inkedFraction(40), inkedFraction(128), inkedFraction(215)

    assert dark > mid > light
    assert 0.4 < mid < 0.6, "a mid grey should come out around half inked"


def testEdgeSourceInksEdgesNotDarkness(cpu):
    """With -e a sub-cell set inks gradient strength, so a flat image gives nothing."""
    charSet = tools.CHARSETS['braille']

    flat = backend.toSubCellGrid(solidImage(30), 10, 10, charSet, cpu, edgeSource = True)
    assert set(flat.flatten()) == {charSet.characterFor(0)}, "a flat image has no edges"

    edged = backend.toSubCellGrid(halfDarkImage(), 10, 10, charSet, cpu, edgeSource = True)
    assert len(set(edged.flatten())) > 1, "a hard edge should be inked"


def testRampSetsStillGoThroughTheNormalPath(grayImage, cpu):
    for name in RAMP_SETS:
        charSet = tools.CHARSETS[name]
        values = backend.toValueGrid(grayImage, 20, 10, cpu)
        grid = backend.toCharGrid(values, charSet.ramp)

        assert grid.shape == (10, 20)
        assert set(grid.flatten()) <= set(charSet.ramp)


def testSubCellGridRejectsARampSet(grayImage, cpu):
    with pytest.raises(tools.Errors.VariableInvalidValueError):
        backend.toSubCellGrid(grayImage, 10, 10, tools.CHARSETS['ascii70'], cpu)


# ================= Half blocks in colour ================

def testHalfBlocksUseOneCharacterAndTwoColors(sampleImage, cpu):
    chars, foreground, background = backend.toHalfBlockColors(sampleImage, 16, 10, cpu)

    assert set(chars.flatten()) == {'▀'}
    assert foreground.shape == (10, 16, 3)
    assert background.shape == (10, 16, 3)


def testHalfBlockColorsComeFromTheRightHalves(cpu):
    """The foreground is the top of each cell and the background the bottom, not the reverse."""
    pixels = np.zeros((40, 20, 3), dtype = np.uint8)
    pixels[:20, :, 0] = 255                                 # top half red
    pixels[20:, :, 2] = 255                                 # bottom half blue
    image = Image.fromarray(pixels, 'RGB')

    _, foreground, background = backend.toHalfBlockColors(image, 4, 2, cpu)

    assert foreground[0, 0, 0] > 200, "top cell's foreground should be the red top"
    assert background[-1, 0, 2] > 200, "bottom cell's background should be the blue bottom"


# ================= Drawing ================

def testBlockCharactersAreDrawnGeometrically():
    """
    Block characters must tile with no seam. Drawn from a font they do not, because the
    glyph fills the em box while the cell is taller than that.
    """
    full = converters.pRenderBlockGlyph('█', 10, 20)
    assert (full > 0).all(), "a full block must cover its whole cell"

    upper = converters.pRenderBlockGlyph('▀', 10, 20)
    assert (upper[:10] > 0).all() and (upper[10:] == 0).all()

    left = converters.pRenderBlockGlyph('▌', 10, 20)
    assert (left[:, :5] > 0).all() and (left[:, 5:] == 0).all()


def testEveryQuadrantCharacterHasGeometry():
    for character in tools.QUADRANT_CHARS:
        assert character in converters.BLOCK_GEOMETRY, f"{character!r} would fall back to the font"


def testShadingCharactersHaveIntermediateCoverage():
    coverage = {char: (converters.pRenderBlockGlyph(char, 16, 16) > 0).mean()
                for char in '░▒▓'}

    assert 0 < coverage['░'] < coverage['▒'] < coverage['▓'] < 1


def testFontIsChosenForTheCharactersActuallyDrawn():
    """
    Most fixed width fonts have no braille at all and silently draw a .notdef box, so the
    font has to be picked from what is being rendered rather than assumed.
    """
    braille = ''.join(chr(0x2800 + value) for value in (0, 1, 0xFF))
    font, width, height = converters.pLoadFont(braille)

    assert converters.pCoversAll(font, set(braille))
    assert width >= 1 and height >= 1


@pytest.mark.parametrize('name', SUB_CELL_SETS + RAMP_SETS)
def testEveryCharsetRendersToAnImage(grayImage, cpu, name):
    """Whatever the set, image output must produce a picture with something drawn in it."""
    charSet = tools.CHARSETS[name]

    if charSet.isSubCell:
        chars = backend.toSubCellGrid(grayImage, 24, 12, charSet, cpu)
    else:
        chars = backend.toCharGrid(backend.toValueGrid(grayImage, 24, 12, cpu), charSet.ramp)

    image = converters.convertToIMG(converters.Conversion(chars))
    distinct = np.unique(np.asarray(image).reshape(-1, 3), axis = 0)

    assert len(distinct) > 1, f"{name} rendered a blank image"
