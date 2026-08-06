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

import xml.etree.ElementTree as ET

import pytest

from src import tools


# ================= Divisors ================

@pytest.mark.parametrize('n', [1, 2, 7, 12, 64, 100, 257, 360, 640, 3840])
def testDivisorsMatchBruteForce(n):
    expected = [i for i in range(1, n + 1) if n % i == 0]

    assert tools.pGetDivisors(n) == expected


def testDivisorsComeBackSorted():
    """The list is shown to the user, so ascending order is part of the behaviour."""
    divisors = tools.pGetDivisors(5040)

    assert divisors == sorted(divisors)
    assert len(set(divisors)) == len(divisors), "a perfect square must not list its root twice"


def testPerfectSquareListsRootOnce():
    assert tools.pGetDivisors(36) == [1, 2, 3, 4, 6, 9, 12, 18, 36]


@pytest.mark.parametrize('n', [0, -1, -100])
def testDivisorsRejectNonPositive(n):
    with pytest.raises(tools.Errors.VariableInvalidValueError):
        tools.pGetDivisors(n)


# ================= Generated names ================

def testGeneratedNameHasThreeParts():
    for _ in range(50):
        assert len(tools.pGetUniqueName().split('_')) == 3


def testGeneratedNamesReachEveryWord():
    """
    Every word in every pool has to be reachable.

    The bounds used to be one short on all three draws, so the last entry of each list
    could never come up: no name ever contained 'Soft', 'Blue' or 'Kettle'.
    """
    everyWord = {word for group in tools.NAME_ADJECTIVES for word in group} | set(tools.NAME_OBJECTS)

    seen = set()
    for _ in range(20_000):
        seen.update(tools.pGetUniqueName().split('_'))

    missing = everyWord - seen
    assert not missing, f"these words can never be generated: {sorted(missing)}"


def testNameWordPoolsHaveNoDuplicates():
    everyWord = [word for group in tools.NAME_ADJECTIVES for word in group] + list(tools.NAME_OBJECTS)

    assert len(everyWord) == len(set(everyWord))


def testGeneratedNamesVary():
    assert len({tools.pGetUniqueName() for _ in range(200)}) > 100


# ================= Colours ================

@pytest.mark.parametrize('rgb,expected', [
    ((0, 0, 0), '#000000'),
    ((255, 255, 255), '#ffffff'),
    ((255, 0, 128), '#ff0080'),
    ((17, 17, 17), '#111111'),
])
def testColorsToHex(rgb, expected):
    assert tools.pColorsToHex(*rgb) == expected


@pytest.mark.parametrize('rgb', [(-1, 0, 0), (0, 256, 0), (0, 0, 300)])
def testColorsToHexRejectsOutOfRange(rgb):
    with pytest.raises(tools.Errors.VariableInvalidValueError):
        tools.pColorsToHex(*rgb)


# ================= Markup escaping ================

@pytest.mark.parametrize('char,expected', [('&', '&amp;'), ('<', '&lt;'), ('>', '&gt;'), ('a', 'a'), (' ', ' ')])
def testEscapeMarkup(char, expected):
    assert tools.pEscapeMarkup(char) == expected


def testEscapeMarkupTextHandlesTheDefaultRamp():
    """
    The 70 character ramp contains '&', '<' and '>', so an unescaped writer produces a
    file that no XML parser will accept.
    """
    escaped = tools.pEscapeMarkupText(tools.GRAYSCALES[70])
    document = f'<root>{escaped}</root>'

    assert ET.fromstring(document).text == tools.GRAYSCALES[70]


def testEscapeMarkupDoesNotDoubleEscape():
    assert tools.pEscapeMarkupText('&lt;') == '&amp;lt;'


# ================= Types and ramps ================

def testValidTypesList():
    assert tools.ValidTypes.asList() == ['txt', 'jpg', 'png', 'xml', 'svg', 'gif', 'mp4']


def testImageTypesAreTheRasterOnes():
    assert set(tools.ValidTypes.getImageTypes()) == {'JPG', 'PNG'}
    assert tools.ValidTypes.JPG.isImage() and tools.ValidTypes.PNG.isImage()
    assert not any(t.isImage() for t in (tools.ValidTypes.TXT, tools.ValidTypes.XML, tools.ValidTypes.SVG))


def testAnimatedTypesHoldSequences():
    assert set(tools.ValidTypes.getAnimatedTypes()) == {'GIF', 'MP4'}
    assert tools.ValidTypes.GIF.isAnimated() and tools.ValidTypes.MP4.isAnimated()
    assert not tools.ValidTypes.PNG.isAnimated()


def testEveryTypeIsExactlyOneKind():
    """Text, image and animated must partition the types, or the writers cannot dispatch."""
    for outputType in tools.ValidTypes:
        kinds = [outputType.isText(), outputType.isImage(), outputType.isAnimated()]
        assert sum(kinds) == 1, f"{outputType.name} is {sum(kinds)} kinds at once"


@pytest.mark.parametrize('given,expected', [
    ('png', tools.ValidTypes.PNG), ('.png', tools.ValidTypes.PNG),
    ('SVG', tools.ValidTypes.SVG), ('.TXT', tools.ValidTypes.TXT),
])
def testFromExtension(given, expected):
    assert tools.ValidTypes.fromExtension(given) == expected


@pytest.mark.parametrize('given', ['.bmp', '', 'jpeg', 'webm'])
def testFromExtensionRejectsUnknown(given):
    with pytest.raises(tools.Errors.VariableInvalidValueError):
        tools.ValidTypes.fromExtension(given)


def testRampsRunDarkToLight():
    """Index 0 must be the dense character, since that is what the mapping assumes."""
    for ramp in tools.GRAYSCALES.values():
        assert ramp[-1] == ' '
        assert ramp[0] != ' '


def testRampLengthsMatchTheirKeys():
    for count, ramp in tools.GRAYSCALES.items():
        assert len(ramp) == count


def testEdgeCharsCoverFourDirections():
    assert tools.EDGE_CHARS == ('|', '/', '-', '\\')


# ================= Errors ================

def testVariableInvalidValueErrorKeepsItsDetails():
    error = tools.Errors.VariableInvalidValueError('cols', 999)

    assert error.varName == 'cols'
    assert error.varValue == 999
    assert 'cols' in str(error) and '999' in str(error)


def testErrorsShareABaseClass():
    for errorType in (tools.Errors.Unimplemented, tools.Errors.VariableNotInitialisedError,
                      tools.Errors.VariableInvalidValueError):
        assert issubclass(errorType, tools.Errors.GenericError)
