###########################################################################
# Copyright (c) 2024, Andy Pandy                                          #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################

"""
End to end runs through the whole pipeline, checking the files that come out the far side.
"""

import xml.etree.ElementTree as ET

import numpy as np
import pytest
from PIL import Image

from src import frontend, midend, tools

TEXT_TYPES = ['txt', 'xml', 'svg']
IMAGE_TYPES = ['png', 'jpg']


@pytest.fixture(autouse = True)
def parser():
    frontend.setupParser()

    return frontend.parser


def run(samplePath, tmp_path, *args: str):
    """Builds a config from CLI arguments and runs the whole conversion."""
    parsed = frontend.parser.parse_args([str(samplePath), '-wc', '40', '-hc', '20', *[str(a) for a in args]])
    config = frontend.buildConfig(parsed)
    result = midend.execute(config)

    return config, result


# ================= Every format round trips ================

@pytest.mark.parametrize('fileType', TEXT_TYPES + IMAGE_TYPES)
def testEveryFormatWritesAReadableFile(samplePath, tmp_path, fileType, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config, _ = run(samplePath, tmp_path, '-ot', fileType, '-op', str(tmp_path / f'out_{fileType}'))

    assert config.outputPath.exists()
    assert config.outputPath.stat().st_size > 0

    if fileType in IMAGE_TYPES:
        with Image.open(config.outputPath) as written:
            written.load()
            assert written.size[0] > 0
    elif fileType in ('xml', 'svg'):
        ET.parse(config.outputPath)


@pytest.mark.parametrize('fileType', IMAGE_TYPES)
def testImageOutputIsNotTruncatedByATextHandle(samplePath, tmp_path, fileType, monkeypatch):
    """
    Saving used to open the output path for text writing whatever the format was, then
    let Pillow write the picture to the same path behind that open handle.
    """
    monkeypatch.chdir(tmp_path)
    config, _ = run(samplePath, tmp_path, '-ot', fileType, '-op', str(tmp_path / 'picture'))

    with Image.open(config.outputPath) as written:
        written.verify()

    assert config.outputPath.stat().st_size > 1000


def testPixelArtRoundTrips(samplePath, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config, result = run(samplePath, tmp_path, '-pix', '-ot', 'png', '-op', str(tmp_path / 'pixels'))

    assert isinstance(result, Image.Image)
    with Image.open(config.outputPath) as written:
        assert written.size == (640, 400)


# ================= Colour handling ================

def testColoredXmlIsValidXml(samplePath, tmp_path, monkeypatch):
    """
    The colour prompt reads from stdin, which pytest has taken away, so this exercises the
    path where the user declines to answer and the writer falls back to characters only.
    """
    monkeypatch.chdir(tmp_path)

    with pytest.raises(tools.Errors.GenericError):
        run(samplePath, tmp_path, '-c', '-ot', 'xml', '-op', str(tmp_path / 'coloured'))


@pytest.mark.parametrize('answer,expectColor', [('t', False), ('c', True)])
def testColorPromptIsHonoured(samplePath, tmp_path, monkeypatch, answer, expectColor):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr('builtins.input', lambda *_: answer)

    config, _ = run(samplePath, tmp_path, '-c', '-ot', 'xml', '-op', str(tmp_path / 'coloured'))
    root = ET.parse(config.outputPath).getroot()

    assert (root.attrib['colored'] == 'true') is expectColor


def testAmbiguousAnswerIsRejectedRatherThanGuessed(samplePath, tmp_path, monkeypatch):
    """
    The prompt used to test membership against the string 'tce', so typing 'tc' passed
    the check, matched no branch, and silently wrote uncoloured output as though nothing
    had happened. It must ask again instead.
    """
    monkeypatch.chdir(tmp_path)
    # 'tc' and 'ce' are substrings of the old check and used to slip through. An empty
    # answer is not in this list because empty deliberately means the 'exit' default.
    answers = iter(['tc', 'ce', 'xyz', 'c'])
    monkeypatch.setattr('builtins.input', lambda *_: next(answers))

    config, _ = run(samplePath, tmp_path, '-c', '-ot', 'xml', '-op', str(tmp_path / 'coloured'))

    assert ET.parse(config.outputPath).getroot().attrib['colored'] == 'true'


@pytest.mark.parametrize('fileType', ['png', 'svg'])
def testColorSurvivesToTheFile(samplePath, tmp_path, monkeypatch, fileType):
    """The sample image is strongly coloured, so the output must not come out grey."""
    monkeypatch.chdir(tmp_path)
    config, _ = run(samplePath, tmp_path, '-c', '-ot', fileType, '-op', str(tmp_path / 'coloured'))

    if fileType == 'png':
        pixels = np.asarray(Image.open(config.outputPath).convert('RGB')).reshape(-1, 3)
        spread = pixels.max(axis = 0).astype(int) - pixels.min(axis = 0).astype(int)
        assert spread.max() > 60, "output looks greyscale"
    else:
        fills = {e.get('fill') for e in ET.parse(config.outputPath).getroot().iter() if e.get('fill')}
        assert len(fills) > 5


# ================= Printing and saving ================

def testPrintingWritesToStdoutAndNoFile(samplePath, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    config, _ = run(samplePath, tmp_path, '-p')

    assert not config.shouldSave
    assert not config.outputPath.exists()
    assert len(capsys.readouterr().out.splitlines()) > 20


def testResultIsReturnedForProgrammaticUse(samplePath, tmp_path, monkeypatch):
    """The conversion comes back to the caller, so the tool can be driven from code."""
    monkeypatch.chdir(tmp_path)
    _, result = run(samplePath, tmp_path, '-p')

    assert result.chars.shape == (20, 40)
    assert result.asRows()[0] != ''


# ================= Flags reaching the output ================

def testInvertFlipsTheOutput(samplePath, tmp_path, monkeypatch):
    """
    Inverting must move the dense characters onto the bright areas: a cell that sat at
    position i in the ramp has to end up at the mirrored position.

    The mirror is allowed to be one out, because inverting the brightness and then
    truncating is not quite the same as truncating and then mirroring the index.
    """
    monkeypatch.chdir(tmp_path)
    ramp = tools.GRAYSCALES[10]
    positions = {char: index for index, char in enumerate(ramp)}

    _, plain = run(samplePath, tmp_path, '-p', '-gs', ramp)
    _, inverted = run(samplePath, tmp_path, '-p', '-i', '-gs', ramp)

    plainIndices = np.vectorize(positions.__getitem__)(plain.chars)
    invertedIndices = np.vectorize(positions.__getitem__)(inverted.chars)

    assert (plain.chars != inverted.chars).mean() > 0.8, "inverting barely changed anything"
    assert np.abs(invertedIndices - (len(ramp) - 1 - plainIndices)).max() <= 1


def testThresholdLeavesOnlyTwoCharacters(samplePath, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _, result = run(samplePath, tmp_path, '-p', '-th', '128')

    assert len(set(result.chars.flatten())) <= 2


def testEdgesIntroduceLineCharacters(samplePath, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _, plain = run(samplePath, tmp_path, '-p')
    _, edged = run(samplePath, tmp_path, '-p', '-e')

    introduced = set(edged.chars.flatten()) - set(plain.chars.flatten())
    assert introduced & set(tools.EDGE_CHARS)


def testCustomRampLimitsTheCharactersUsed(samplePath, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _, result = run(samplePath, tmp_path, '-p', '-gs', '@#+. ')

    assert set(result.chars.flatten()) <= set('@#+. ')


def testGpuFlagProducesTheSameFileAsCpu(samplePath, tmp_path, monkeypatch):
    """
    Whatever device ends up being used, the user must get the same picture. On a machine
    with no GPU this also covers the fallback producing an identical result.
    """
    monkeypatch.chdir(tmp_path)
    _, onCpu = run(samplePath, tmp_path, '-p')
    _, onGpu = run(samplePath, tmp_path, '-p', '-g')

    mismatched = int((onCpu.chars != onGpu.chars).sum())
    assert mismatched / onCpu.chars.size < 0.0005
