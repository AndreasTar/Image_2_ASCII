###########################################################################
# Copyright (c) 2024, Andy Pandy                                          #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################

"""
Checks the vectorised core against the tile-at-a-time original in tests/reference.py.

The rewrite is only worth having if it produces the same picture, so these are the tests
that matter most. They compare against the old algorithm rather than a stored file,
so the expected result stays re-derivable.
"""

import numpy as np
import pytest
from PIL import Image

from src import backend, compute, tools
from tests import reference
from tests.conftest import GRID_CASES

RAMP = tools.GRAYSCALES[70]


@pytest.fixture(scope = 'module')
def cpu():
    return compute.getCpuBackend()


def referenceChars(image: Image.Image, cols: int, rows: int, charList: str = RAMP) -> np.ndarray:
    """Runs the original algorithm and returns its output as a 2D character grid."""
    lines = reference.convert2Ascii(image, image.size[0], image.size[1], cols, rows, charList)

    return np.array([list(line) for line in lines])


def rampIndices(chars: np.ndarray, charList: str = RAMP) -> np.ndarray:
    """Maps a character grid back to its positions in the ramp, so grids can be compared numerically."""
    lookup = {char: index for index, char in enumerate(charList)}

    return np.vectorize(lookup.__getitem__)(chars)


def bruteForceBlockMean(image: Image.Image, cols: int, rows: int) -> np.ndarray:
    """The block mean written out the obvious way, one tile at a time, in full precision."""
    pixels = np.asarray(image, dtype = np.float64)
    yEdges = backend.pTileEdges(pixels.shape[0], rows)
    xEdges = backend.pTileEdges(pixels.shape[1], cols)

    return np.array([[pixels[yEdges[r]:yEdges[r + 1], xEdges[c]:xEdges[c + 1]].mean()
                      for c in range(cols)] for r in range(rows)])


# ================= The golden tests ================

@pytest.mark.parametrize('cols,rows', GRID_CASES)
def testMatchesExactBlockMean(grayImage, cpu, cols, rows):
    """
    The tool's definition of a tile average, checked against the obvious slow version.

    This is the test that pins the maths down. Pillow's BOX resampling was the obvious
    thing to reach for here and is roughly twice as quick, but it fails this check by up
    to 11 grayscale levels on some grid sizes, which is why it is not used.
    """
    expected = bruteForceBlockMean(grayImage, cols, rows)
    actual = backend.toValueGrid(grayImage, cols, rows, cpu)

    assert actual.shape == expected.shape
    assert np.abs(actual - expected).max() < 1e-3


@pytest.mark.parametrize('cols,rows', [(97, 61), (128, 64), (31, 29), (80, 25), (64, 40)])
def testMatchesExactBlockMeanOnNoise(noiseImage, cpu, cols, rows):
    """Noise has no smooth areas, so a misplaced tile boundary cannot go unnoticed."""
    expected = bruteForceBlockMean(noiseImage, cols, rows)
    actual = backend.toValueGrid(noiseImage, cols, rows, cpu)

    assert np.abs(actual - expected).max() < 1e-3


@pytest.mark.parametrize('cols,rows', GRID_CASES)
def testAgreesWithOriginalAlgorithm(grayImage, cpu, cols, rows):
    """
    The rewrite must still produce the picture the old tile loop produced.

    Two deliberate differences are allowed, both worth at most one step of the ramp. The
    original truncated each tile average to a whole number before picking a character, and
    it cut tiles with Pillow's crop, which breaks a tie on an exact half pixel the other
    way from the block mean. Anything beyond one step would mean the tiles really moved.
    """
    expected = rampIndices(referenceChars(grayImage, cols, rows))
    actual = rampIndices(backend.toCharGrid(backend.toValueGrid(grayImage, cols, rows, cpu), RAMP))

    assert actual.shape == expected.shape
    assert np.abs(actual.astype(int) - expected.astype(int)).max() <= 1


@pytest.mark.parametrize('cols,rows', [(64, 40), (80, 25), (32, 20)])
def testAgreesWithOriginalAlgorithmExactlyOnEvenGrids(grayImage, cpu, cols, rows):
    """
    Where the grid divides the image evenly there are no tie breaks to differ over, so
    the only remaining difference is the original's truncation. Replicating that one step
    makes the two agree cell for cell.
    """
    expected = referenceChars(grayImage, cols, rows)
    actual = backend.toCharGrid(np.floor(backend.toValueGrid(grayImage, cols, rows, cpu)), RAMP)

    assert np.array_equal(actual, expected)


# ================= Block mean ================

def testValueGridIsPlainBlockMean(cpu):
    """A grid built from known blocks must come back as exactly those block averages."""
    pixels = np.repeat(np.repeat(np.array([[0, 100], [200, 255]], dtype = np.uint8), 20, 0), 20, 1)
    grid = backend.toValueGrid(Image.fromarray(pixels, 'L'), 2, 2, cpu)

    assert np.allclose(grid, [[0, 100], [200, 255]], atol = 1e-4)


def testTileEdgesCoverEveryPixelExactlyOnce(cpu):
    """No pixel may be dropped or counted twice, whatever the grid size."""
    for size, count in [(640, 113), (400, 37), (257, 256), (100, 1), (99, 99)]:
        edges = backend.pTileEdges(size, count)

        assert edges[0] == 0
        assert edges[-1] == size
        assert np.all(np.diff(edges) >= 1), "a tile ended up with no pixels in it"


def testValueGridSpansFullRange(grayImage, cpu):
    grid = backend.toValueGrid(grayImage, 80, 25, cpu)

    assert 0 <= grid.min() and grid.max() <= 255


@pytest.mark.parametrize('cols,rows', [(0, 10), (10, 0), (10_000, 10), (10, 10_000), (-1, 5)])
def testRejectsImpossibleGrids(grayImage, cpu, cols, rows):
    with pytest.raises(tools.Errors.VariableInvalidValueError):
        backend.toValueGrid(grayImage, cols, rows, cpu)


# ================= Character mapping ================

def testCharGridUsesDenseCharactersOnDarkAreas():
    values = np.array([[0.0, 255.0]])
    chars = backend.toCharGrid(values, '@ ')

    assert chars[0, 0] == '@'
    assert chars[0, 1] == ' '


def testInvertSwapsTheEnds():
    values = np.array([[0.0, 255.0]])
    chars = backend.toCharGrid(values, '@ ', invert = True)

    assert chars[0, 0] == ' '
    assert chars[0, 1] == '@'


def testThresholdCollapsesToTwoTones():
    values = np.array([[0.0, 120.0, 130.0, 255.0]])
    chars = backend.toCharGrid(values, '@#+- ', threshold = 128)

    assert set(chars.flatten()) == {'@', ' '}
    assert list(chars[0]) == ['@', '@', ' ', ' ']


def testCharGridRejectsEmptyRamp():
    with pytest.raises(tools.Errors.VariableInvalidValueError):
        backend.toCharGrid(np.zeros((2, 2)), '')


def testEveryRampCharacterIsReachable():
    """A ramp is no use if its last character can never be selected."""
    values = np.linspace(0, 255, 512).reshape(1, -1)

    for ramp in (tools.GRAYSCALES[10], tools.GRAYSCALES[70], '@#+. '):
        assert set(backend.toCharGrid(values, ramp).flatten()) == set(ramp)


# ================= Edges ================

def testEdgeDirectionsFollowTheEdge(cpu):
    """A hard vertical edge must be drawn with a vertical character, and so on round."""
    cases = {
        '|' : lambda a: a.__setitem__((slice(None), slice(50, None)), 255),      # vertical split
        '-' : lambda a: a.__setitem__((slice(50, None), slice(None)), 255),      # horizontal split
    }

    for expected, paint in cases.items():
        pixels = np.zeros((100, 100), dtype = np.uint8)
        paint(pixels)
        image = Image.fromarray(pixels, 'L')

        magnitude, angle = backend.toEdgeGrids(image, 20, 20, cpu)
        chars = backend.applyEdges(np.full((20, 20), '.'), magnitude, angle, 90)
        drawn = set(chars.flatten()) - {'.'}

        assert drawn == {expected}, f"expected only '{expected}' edges, got {drawn}"


def testFlatImageProducesNoEdges(cpu):
    """A percentile cutoff must not promote the noise floor of a flat image into edges."""
    flat = Image.new('L', (200, 200), 128)
    magnitude, angle = backend.toEdgeGrids(flat, 20, 20, cpu)
    chars = backend.applyEdges(np.full((20, 20), '.'), magnitude, angle, 50)

    assert set(chars.flatten()) == {'.'}


def testLowerSensitivityFindsMoreEdges(grayImage, cpu):
    magnitude, angle = backend.toEdgeGrids(grayImage, 80, 25, cpu)
    blank = np.full((25, 80), '.')

    many = (backend.applyEdges(blank, magnitude, angle, 60) != '.').sum()
    few = (backend.applyEdges(blank, magnitude, angle, 95) != '.').sum()

    assert many > few


# ================= Alpha and pixelart ================

def testFlattenAlphaCompositesOntoBlack():
    """Transparent white must read as black, not as white."""
    image = Image.new('RGBA', (10, 10), (255, 255, 255, 0))
    flattened = backend.flattenAlpha(image)

    assert np.asarray(flattened.convert('L')).max() == 0


def testFlattenAlphaLeavesOpaqueImagesAlone(sampleImage):
    assert backend.flattenAlpha(sampleImage) is sampleImage


def testPixelArtKeepsOriginalSize(sampleImage):
    result = backend.convert2Pixel(sampleImage, sampleImage.size, 40, 25)

    assert result.size == sampleImage.size


def testPixelArtProducesFlatBlocks():
    """Every pixel inside one output block must share a value."""
    pixels = np.random.default_rng(0).integers(0, 256, (40, 40), dtype = np.uint8)
    result = backend.convert2Pixel(Image.fromarray(pixels, 'L'), (40, 40), 4, 4)
    array = np.asarray(result)

    for row in range(4):
        for col in range(4):
            block = array[row * 10:(row + 1) * 10, col * 10:(col + 1) * 10]
            assert block.min() == block.max()


# ================= Colours ================

def testColorGridTracksPositionNotStride(cpu):
    """
    Colours must stay attached to their own cell on a non-square grid.

    The old code indexed a flat colour list with the row length of the *other* axis, which
    left every non-square output with its colours shuffled.
    """
    pixels = np.zeros((60, 20, 3), dtype = np.uint8)
    pixels[:, :, 0] = 255                                   # top-left quadrant marker
    pixels[30:, :, 0] = 0
    pixels[30:, :, 1] = 255
    image = Image.fromarray(pixels, 'RGB')

    grid = backend.toColorGrid(image, 2, 6, cpu)

    assert grid.shape == (6, 2, 3)
    assert (grid[:3, :, 0] == 255).all(), "top half should still be red"
    assert (grid[3:, :, 1] == 255).all(), "bottom half should still be green"


def testColorGridAcceptsPaletteAndGrayscaleInputs(sampleImage, cpu):
    """getchannel('R') used to blow up on anything that was not already RGB."""
    for image in (sampleImage.convert('P'), sampleImage.convert('L'), sampleImage.convert('RGBA')):
        grid = backend.toColorGrid(image, 8, 5, cpu)

        assert grid.shape == (5, 8, 3)
        assert grid.dtype == np.uint8


# ================= Band threshold ================

def testBandKeepsBothEndsInclusive():
    values = np.array([[0, 60, 128, 200, 255]], dtype = np.float32)

    assert backend.bandMask(values, 60, 200).tolist() == [[False, True, True, True, False]]


def testBandGivenBackwardsIsReadAsTheRangeBetween():
    """Two sliders dragged past each other is a slip, not a request for a blank picture."""
    values = np.array([[10, 100, 250]], dtype = np.float32)

    assert backend.bandMask(values, 200, 50).tolist() == backend.bandMask(values, 50, 200).tolist()


def testBandLeavesWhatItKeepsExactlyAsItWas(grayImage, cpu):
    """
    The whole promise of the feature: inside the band it is as if no band were set.

    A two-tone threshold rewrites every value it is handed. This one only decides what
    survives, so every surviving cell has to be character-for-character identical.
    """
    values = backend.toValueGrid(grayImage, 80, 40, cpu)
    plain = backend.toCharGrid(values, RAMP)
    banded = backend.applyBand(plain, values, 90, 170)

    keep = backend.bandMask(values, 90, 170)

    assert keep.any() and not keep.all(), "the band should have removed some cells but not all"
    assert (banded[keep] == plain[keep]).all()
    assert (banded[~keep] == ' ').all()


def testBandBlanksWithTheCharacterSetsOwnEmptyGlyph():
    """
    A space in a braille run is a hole of the wrong width. Every sub-cell set has a
    character with no dots lit, which is the right kind of nothing.
    """
    assert tools.CHARSETS['ascii70'].blank == ' '
    assert tools.CHARSETS['braille'].blank == '\u2800'
    assert tools.CHARSETS['quadrants'].blank == ' '
    assert tools.CHARSETS['halfblocks'].blank == ' '


def testPunchOutBandMakesPixelArtTransparentOutsideTheBand(sampleImage, cpu):
    values = backend.toValueGrid(sampleImage.convert('L'), 40, 25, cpu)
    blocks = backend.convert2Pixel(sampleImage.convert('RGB'), sampleImage.size, 40, 25)
    punched = backend.punchOutBand(blocks, values, 90, 170)

    alpha = np.asarray(punched)[..., 3]

    assert punched.mode == 'RGBA'
    assert punched.size == blocks.size
    assert set(np.unique(alpha).tolist()) <= {0, 255}, "cells are wholly kept or wholly removed"
    assert (alpha == 0).any() and (alpha == 255).any()


def testPunchedHolesLineUpWithTheBlocks(sampleImage, cpu):
    """
    The mask is built at grid resolution and blown up the same way the picture is, so a
    hole covers exactly one block rather than straddling two.
    """
    cols, rows = 40, 25
    values = backend.toValueGrid(sampleImage.convert('L'), cols, rows, cpu)
    blocks = backend.convert2Pixel(sampleImage.convert('RGB'), sampleImage.size, cols, rows)
    alpha = np.asarray(backend.punchOutBand(blocks, values, 90, 170))[..., 3]

    keep = backend.bandMask(values, 90, 170)
    shrunk = np.asarray(Image.fromarray(alpha, 'L').resize((cols, rows), Image.Resampling.NEAREST))

    assert ((shrunk > 127) == keep).all()
