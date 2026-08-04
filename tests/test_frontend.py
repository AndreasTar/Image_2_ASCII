###########################################################################
# Copyright (c) 2024, Andy Pandy                                          #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################

import pathlib as pl

import pytest

from src import frontend, tools


@pytest.fixture(autouse = True)
def parser():
    """The parser is module level state, so it gets rebuilt for every test."""
    frontend.setupParser()

    return frontend.parser


def parse(*args: str):
    return frontend.parser.parse_args([str(a) for a in args])


def buildConfig(samplePath, *args: str):
    return frontend.buildConfig(parse(samplePath, *args))


# ================= Parsing ================

def testInputFileIsRequired():
    with pytest.raises(SystemExit):
        parse()


def testDefaults(samplePath):
    args = parse(samplePath)

    assert args.inputGSCount == 70
    assert args.inputFileTypeOut == 'txt'
    assert args.inputFileNameOut == 'RANDOM'
    assert args.inputGpu is None
    assert args.inputCharAspect == tools.DEFAULT_CHAR_ASPECT
    assert not any([args.inputColored, args.inputPixelated, args.inputInvert,
                    args.inputEdges, args.inputPrint, args.inputAlpha, args.inputAuto])


@pytest.mark.parametrize('flags', [
    ('-wi', '10', '-wc', '20'),
    ('-hi', '10', '-hc', '20'),
    ('-gsc', '10', '-pix'),
    ('-gs', '@# ', '-pix'),
    ('-gsc', '10', '-gs', '@# '),
])
def testMutuallyExclusiveFlagsAreRejected(samplePath, flags):
    with pytest.raises(SystemExit):
        parse(samplePath, *flags)


@pytest.mark.parametrize('given,expected', [([], None), (['-g'], 'auto'),
                                            (['-g', 'cupy'], 'cupy'), (['-g', 'torch'], 'torch')])
def testGpuFlagIsOptionalWithAnOptionalValue(samplePath, given, expected):
    assert parse(samplePath, *given).inputGpu == expected


def testGpuFlagRejectsUnknownBackend(samplePath):
    with pytest.raises(SystemExit):
        parse(samplePath, '-g', 'opencl')


@pytest.mark.parametrize('flag,value', [('-th', '256'), ('-th', '-1'), ('-et', '101'), ('-ca', '0'), ('-ca', '-2')])
def testOutOfRangeValuesAreRejected(samplePath, flag, value):
    with pytest.raises(SystemExit):
        parse(samplePath, flag, value)


@pytest.mark.parametrize('flag,value', [('-th', '0'), ('-th', '255'), ('-et', '0'), ('-et', '100'), ('-ca', '0.43')])
def testInRangeValuesAreAccepted(samplePath, flag, value):
    parse(samplePath, flag, value)


# ================= Output resolution ================

def testOutputPathDefaultsToRandomNameInWorkingDirectory(samplePath, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    config = buildConfig(samplePath, '-wc', '10', '-hc', '10')

    assert config.outputPath.parent == tmp_path
    assert config.outputPath.suffix == '.txt'
    assert len(config.outputPath.stem.split('_')) == 3


def testInputNamingUsesTheSourceStem(samplePath, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    config = buildConfig(samplePath, '-wc', '10', '-hc', '10', '-on', 'INPUT')

    assert config.outputPath.name == 'sample.txt'


def testInputNamingHandlesLongExtensions(sampleImage, monkeypatch, tmp_path):
    """
    The stem used to be taken by chopping four characters off the end, which mangled any
    extension that was not three letters long.
    """
    monkeypatch.chdir(tmp_path)
    source = tmp_path / 'holiday.jpeg'
    sampleImage.save(source)

    config = buildConfig(source, '-wc', '10', '-hc', '10', '-on', 'INPUT')

    assert config.outputPath.name == 'holiday.txt'


def testExtensionIsAppendedWhenMissing(samplePath, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    config = buildConfig(samplePath, '-wc', '10', '-hc', '10', '-op', 'result', '-ot', 'svg')

    assert config.outputPath.name == 'result.svg'


def testExtensionIsNotDoubledWhenAlreadyPresent(samplePath, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    config = buildConfig(samplePath, '-wc', '10', '-hc', '10', '-op', 'result.png', '-ot', 'png')

    assert config.outputPath.name == 'result.png'


def testMissingParentFoldersAreCreated(samplePath, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    config = buildConfig(samplePath, '-wc', '10', '-hc', '10', '-op', 'deep/nested/result')

    assert config.outputPath.parent.is_dir()
    assert config.outputPath.name == 'result.txt'


# ================= Validation ================

def testPixelArtRejectsTextOutput(samplePath):
    with pytest.raises(SystemExit):
        buildConfig(samplePath, '-wc', '10', '-hc', '10', '-pix', '-ot', 'txt')


@pytest.mark.parametrize('fileType', ['png', 'jpg'])
def testPixelArtAcceptsImageOutput(samplePath, monkeypatch, tmp_path, fileType):
    monkeypatch.chdir(tmp_path)
    config = buildConfig(samplePath, '-wc', '10', '-hc', '10', '-pix', '-ot', fileType)

    assert config.pixelated


def testPrintRejectsImageOutput(samplePath):
    """There is nothing sensible to write to a terminal for a PNG."""
    with pytest.raises(SystemExit):
        buildConfig(samplePath, '-wc', '10', '-hc', '10', '-p', '-ot', 'png')


def testMissingInputFileExitsCleanly(tmp_path):
    with pytest.raises(SystemExit):
        buildConfig(tmp_path / 'nope.png', '-wc', '10', '-hc', '10')


def testNonImageInputExitsCleanly(tmp_path):
    notAnImage = tmp_path / 'notes.png'
    notAnImage.write_text('this is not a picture')

    with pytest.raises(SystemExit):
        buildConfig(notAnImage, '-wc', '10', '-hc', '10')


def testEmptyCustomRampIsRejected(samplePath):
    with pytest.raises(SystemExit):
        buildConfig(samplePath, '-wc', '10', '-hc', '10', '-gs', '')


# ================= Grid resolution ================

def testTileCountsAreUsedAsGiven(samplePath, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    config = buildConfig(samplePath, '-wc', '64', '-hc', '40')

    assert (config.widthCount, config.heightCount) == (64, 40)


def testPixelsPerTileBecomeATileCount(samplePath, monkeypatch, tmp_path):
    """640 wide in 10 pixel tiles is 64 tiles; 400 tall in 16 pixel tiles is 25."""
    monkeypatch.chdir(tmp_path)
    config = buildConfig(samplePath, '-wi', '10', '-hi', '16')

    assert (config.widthCount, config.heightCount) == (64, 25)


def testPixelsPerTileRoundUpForRemainders(samplePath, monkeypatch, tmp_path):
    """A leftover strip still needs a tile of its own."""
    monkeypatch.chdir(tmp_path)
    config = buildConfig(samplePath, '-wi', '300', '-hi', '300')

    assert (config.widthCount, config.heightCount) == (3, 2)


def testAutoDerivesBothAxes(samplePath, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    config = buildConfig(samplePath, '-a')

    assert 1 <= config.widthCount <= 640
    assert 1 <= config.heightCount <= 400


def testAutoAppliesTheCharacterAspectRatio(samplePath, monkeypatch, tmp_path):
    """
    A 640x400 image at 100 columns should come out 100 * 0.5 * 400/640 = 31 rows, so that
    the cells, which are twice as tall as they are wide, still add up to the right shape.
    """
    monkeypatch.chdir(tmp_path)
    config = buildConfig(samplePath, '-a', '-wc', '100')

    assert (config.widthCount, config.heightCount) == (100, 31)


def testAutoFillsInOnlyTheMissingAxis(samplePath, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    config = buildConfig(samplePath, '-a', '-hc', '50')

    assert config.heightCount == 50
    assert config.widthCount == round(50 * 640 / (tools.DEFAULT_CHAR_ASPECT * 400))


def testCharAspectChangesTheDerivedAxis(samplePath, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    wide = buildConfig(samplePath, '-a', '-wc', '100', '-ca', '1.0')
    tall = buildConfig(samplePath, '-a', '-wc', '100', '-ca', '0.5')

    assert wide.heightCount == 2 * tall.heightCount


def testAutoNeverProducesAnEmptyGrid(sampleImage, monkeypatch, tmp_path):
    """A very wide, very short image must still get at least one row."""
    monkeypatch.chdir(tmp_path)
    source = tmp_path / 'strip.png'
    sampleImage.resize((640, 4)).save(source)

    config = buildConfig(source, '-a', '-wc', '200')

    assert config.heightCount >= 1


# ================= Ramps and saving behaviour ================

def testCustomRampIsUsed(samplePath, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    config = buildConfig(samplePath, '-wc', '10', '-hc', '10', '-gs', '@#+. ')

    assert config.charList == '@#+. '


@pytest.mark.parametrize('count', [10, 70])
def testBuiltInRampsAreSelectable(samplePath, monkeypatch, tmp_path, count):
    monkeypatch.chdir(tmp_path)
    config = buildConfig(samplePath, '-wc', '10', '-hc', '10', '-gsc', str(count))

    assert config.charList == tools.GRAYSCALES[count]


def testPrintingAloneDoesNotWriteAFile(samplePath, monkeypatch, tmp_path):
    """Asking to see the result on screen should not litter the folder with output."""
    monkeypatch.chdir(tmp_path)
    config = buildConfig(samplePath, '-wc', '10', '-hc', '10', '-p')

    assert config.printToScreen
    assert not config.shouldSave


def testPrintingWithAnExplicitPathStillSaves(samplePath, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    config = buildConfig(samplePath, '-wc', '10', '-hc', '10', '-p', '-op', 'wanted')

    assert config.printToScreen and config.shouldSave


def testGpuRequestFallsBackWithoutFailing(samplePath, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    config = buildConfig(samplePath, '-wc', '10', '-hc', '10', '-g')

    assert config.backend is not None
    assert isinstance(config.backend.deviceName, str)


def testConfigIsAFreshObjectEachTime(samplePath, monkeypatch, tmp_path):
    """
    Configuration used to be written onto the class itself, so two conversions in one
    process shared, and overwrote, each other's settings.
    """
    monkeypatch.chdir(tmp_path)
    first = buildConfig(samplePath, '-wc', '10', '-hc', '10', '-i')
    second = buildConfig(samplePath, '-wc', '20', '-hc', '20')

    assert first is not second
    assert first.invert and not second.invert
    assert (first.widthCount, second.widthCount) == (10, 20)
