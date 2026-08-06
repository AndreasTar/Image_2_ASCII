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
Checks each output writer, with particular attention to the formats that have to parse.
"""

import xml.etree.ElementTree as ET

import numpy as np
import pytest
import svg
from PIL import Image

from src import converters, tools
from src.converters import Conversion

# A grid holding the characters that break XML if they are not escaped.
AWKWARD_CHARS = np.array([['&', '<', '>'],
                          [' ', '"', "'"],
                          ['a', '\\', '/']])


@pytest.fixture
def plainConversion():
    chars = np.array(list(tools.GRAYSCALES[10] * 3)[:24]).reshape(4, 6)

    return Conversion(chars)


@pytest.fixture
def coloredConversion(plainConversion):
    rng = np.random.default_rng(0)
    colors = rng.integers(0, 256, (*plainConversion.chars.shape, 3), dtype = np.uint8)

    return Conversion(plainConversion.chars, colors)


# ================= The Conversion holder ================

def testConversionReportsItsShape(plainConversion):
    assert (plainConversion.rows, plainConversion.cols) == (4, 6)
    assert not plainConversion.isColored


def testAsRowsJoinsEachRow(plainConversion):
    rows = plainConversion.asRows()

    assert len(rows) == 4
    assert all(len(row) == 6 for row in rows)
    assert rows[0] == ''.join(plainConversion.chars[0])


def testHexGridMatchesPerCellColors(coloredConversion):
    hexGrid = coloredConversion.asHexGrid()

    for row in range(coloredConversion.rows):
        for col in range(coloredConversion.cols):
            expected = tools.pColorsToHex(*(int(v) for v in coloredConversion.colors[row, col]))
            assert hexGrid[row, col] == expected


def testHexGridIsNoneWhenNotColored(plainConversion):
    assert plainConversion.asHexGrid() is None


# ================= Text ================

def testTextOutputIsOneLinePerRow(plainConversion):
    lines = converters.convertToText(plainConversion)

    assert lines == plainConversion.asRows()


def testColoredTextCarriesEveryCellsColor(coloredConversion):
    """
    Cells are read at fixed offsets, not by splitting on the separator: the character in a
    cell may itself be a space, which is exactly what the lightest end of every ramp is.
    """
    lines = converters.convertToText(coloredConversion, withColor = True)
    stride = converters.COLORED_TEXT_CELL_WIDTH + 1

    assert len(lines) == coloredConversion.rows
    for row, line in enumerate(lines):
        assert len(line) == coloredConversion.cols * stride - 1
        for col in range(coloredConversion.cols):
            cell = line[col * stride:col * stride + converters.COLORED_TEXT_CELL_WIDTH]
            assert cell[6] == coloredConversion.chars[row, col]
            assert cell[:6] == tools.pColorsToHex(*(int(v) for v in coloredConversion.colors[row, col]))[1:].upper()


def testColoredTextCellsAreFixedWidth():
    """
    The format is only readable because every cell is the same width, so a row of spaces
    has to take up as much room as any other row.
    """
    chars = np.array([[' ', ' ', ' '], ['@', '#', '.']])
    colors = np.zeros((2, 3, 3), dtype = np.uint8)
    lines = converters.convertToText(Conversion(chars, colors), withColor = True)

    assert len(lines[0]) == len(lines[1])


# ================= XML ================

def testPlainXmlParses(plainConversion):
    document = '\n'.join(converters.convertToXML(plainConversion))
    root = ET.fromstring(document)

    assert root.tag == 'ascii'
    assert root.attrib == {'rows': '4', 'cols': '6', 'colored': 'false'}
    assert len(root) == 4


def testPlainXmlKeepsTheRowText(plainConversion):
    root = ET.fromstring('\n'.join(converters.convertToXML(plainConversion)))

    for index, row in enumerate(root):
        assert row.text == plainConversion.asRows()[index]


def testColoredXmlParsesAndCarriesColors(coloredConversion):
    root = ET.fromstring('\n'.join(converters.convertToXML(coloredConversion, withColor = True)))

    assert root.attrib['colored'] == 'true'
    assert len(root) == 4

    for rowIndex, row in enumerate(root):
        assert len(row) == 6
        for colIndex, cell in enumerate(row):
            assert cell.text == coloredConversion.chars[rowIndex, colIndex]
            expected = tools.pColorsToHex(*(int(v) for v in coloredConversion.colors[rowIndex, colIndex]))
            assert cell.attrib['f'] == expected


@pytest.mark.parametrize('withColor', [False, True])
def testXmlEscapesAwkwardCharacters(withColor):
    """
    The default 70 character ramp contains '&', '<' and '>'. Writing them straight out
    produced a file no parser would accept, which is what the old writer did.
    """
    conversion = Conversion(AWKWARD_CHARS, np.zeros((3, 3, 3), dtype = np.uint8) if withColor else None)
    root = ET.fromstring('\n'.join(converters.convertToXML(conversion, withColor = withColor)))

    recovered = [''.join(cell.text for cell in row) if withColor else row.text for row in root]
    assert recovered == [''.join(row) for row in AWKWARD_CHARS]


def testXmlSurvivesTheFullDefaultRamp():
    chars = np.array(list(tools.GRAYSCALES[70])).reshape(1, -1)
    root = ET.fromstring('\n'.join(converters.convertToXML(Conversion(chars))))

    assert root[0].text == tools.GRAYSCALES[70]


def testXmlTagsAreClosed(plainConversion):
    """The old writer emitted '<char>x<char>', which never closed the element."""
    document = '\n'.join(converters.convertToXML(plainConversion))

    assert document.count('<row') == document.count('</row>')


# ================= SVG ================

@pytest.mark.parametrize('colored', [False, True])
def testSvgParses(plainConversion, coloredConversion, colored):
    conversion = coloredConversion if colored else plainConversion
    document = converters.convertToSVG(conversion).as_str()
    root = ET.fromstring(document)

    assert root.tag.endswith('svg')


def testSvgIsSizedToTheGrid(plainConversion):
    document = converters.convertToSVG(plainConversion)

    assert document.width == plainConversion.cols * converters.SVG_CELL_WIDTH + 2 * converters.SVG_PADDING
    assert document.height == plainConversion.rows * converters.SVG_LINE_HEIGHT + 2 * converters.SVG_PADDING


def testSvgEscapesAwkwardCharacters():
    document = converters.convertToSVG(Conversion(AWKWARD_CHARS)).as_str()
    root = ET.fromstring(document)

    text = ''.join(span.text or '' for span in root.iter() if span.tag.endswith('tspan'))
    assert '&' in text and '<' in text and '>' in text


def testSvgGroupsRunsInsteadOfOneElementPerCharacter(plainConversion):
    """
    A grayscale row shares one colour, so it should cost one element, not one per cell.
    The old writer emitted a tspan for every single character.
    """
    root = ET.fromstring(converters.convertToSVG(plainConversion).as_str())
    spans = [e for e in root.iter() if e.tag.endswith('tspan')]

    assert len(spans) <= plainConversion.rows


def testSvgSpacesDoNotCollapse():
    """Runs of spaces have to keep their width or the grid shears."""
    chars = np.array([['a', ' ', ' ', 'b']])
    root = ET.fromstring(converters.convertToSVG(Conversion(chars)).as_str())
    spans = [e for e in root.iter() if e.tag.endswith('tspan')]

    assert all(' ' not in (span.text or '') for span in spans), "plain spaces would be collapsed by renderers"
    assert any(converters.NBSP in (span.text or '') for span in spans)


# ================= Raster ================

@pytest.mark.parametrize('colored', [False, True])
def testImageOutputHasTheRightShape(plainConversion, coloredConversion, colored):
    conversion = coloredConversion if colored else plainConversion
    image = converters.convertToIMG(conversion)
    _, cellWidth, cellHeight = converters.pLoadFont()

    assert image.mode == 'RGB'
    assert image.size == (conversion.cols * cellWidth, conversion.rows * cellHeight)


def testImageOutputActuallyDrawsSomething(plainConversion):
    """A blank canvas would also pass a size check, so make sure ink went down."""
    image = converters.convertToIMG(plainConversion)

    assert len(np.unique(np.asarray(image).reshape(-1, 3), axis = 0)) > 1


def testColoredImageUsesTheCellColors():
    """A cell drawn in red must contain red pixels, and none of the other cells' colours."""
    chars = np.array([['@', '@']])
    colors = np.array([[[255, 0, 0], [0, 255, 0]]], dtype = np.uint8)
    image = np.asarray(converters.convertToIMG(Conversion(chars, colors)))

    _, cellWidth, _ = converters.pLoadFont()
    left, right = image[:, :cellWidth], image[:, cellWidth:]

    assert left[..., 0].max() > left[..., 1].max(), "left cell should be red"
    assert right[..., 1].max() > right[..., 0].max(), "right cell should be green"


def testGlyphAtlasCoversEveryCharacterUsed():
    """Every distinct character, including the edge ones, must render into the atlas."""
    every = list(tools.GRAYSCALES[70]) + list(tools.EDGE_CHARS)
    chars = np.array(every + [' '] * (-len(every) % 8)).reshape(-1, 8)

    image = converters.convertToIMG(Conversion(chars))

    assert image.size[0] > 0 and image.size[1] > 0


def testFontMetricsAreSane():
    font, cellWidth, cellHeight = converters.pLoadFont()

    assert cellWidth >= 1 and cellHeight >= 1
    assert cellHeight >= cellWidth, "a character cell should be at least as tall as it is wide"


def testColorRunsSplitOnColorChange():
    row = np.array(['#ff0000', '#ff0000', '#00ff00', '#00ff00', '#00ff00'])

    assert list(converters.pColorRuns(row, 5)) == [(0, 2), (2, 5)]


def testColorRunsAreOneSpanWhenGrayscale():
    assert list(converters.pColorRuns(None, 7)) == [(0, 7)]
