###########################################################################
# Copyright (c) 2024-2026, Andy Pandy                                          #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################

"""
The GUI's translation layer, tested without a GUI.

`gui.session` turns what the controls say into a `Config`, and deliberately imports no Qt,
so all of it can be checked here. Anything that needs a widget on screen is not in scope;
what matters is that the settings a user can express come out as a conversion the engine
will accept, and that the ones it cannot honour are refused rather than half done.
"""

import ast
import builtins
import pathlib as pl
import shlex

import pytest
from PIL import Image

from gui import session
from src import frontend, midend, tools

# What the panel hands over with nothing touched. Individual tests override single keys,
# which keeps each one about the setting it is actually exercising.
DEFAULTS = {
    'widthMode':        'count',
    'widthValue':       40,
    'heightMode':       'count',
    'heightValue':      20,
    'charAspect':       0.5,
    'charMode':         'rampSize',
    'rampSize':         70,
    'charsetName':      'blocks',
    'customRamp':       '',
    'colored':          False,
    'invert':           False,
    'dither':           False,
    'alpha':            False,
    'threshold':        None,
    'band':             None,
    'edges':            False,
    'edgeSensitivity':  90,
    'maxFrames':        None,
    'frameStep':        1,
    'fps':              None,
    'writeFrames':      False,
    'outputType':       'txt',
    'embedColor':       False,
    'gpu':              None,
}


def settings(**overrides) -> dict:
    return {**DEFAULTS, **overrides}


def testDefaultsCoverEverySettingTheSessionReads():
    """
    Catches a control being added to the panel and read here without this fixture learning
    about it, which otherwise shows up as a KeyError in whichever test happened to run
    first rather than as a statement about what is missing.
    """
    with open(session.__file__, encoding = 'utf-8') as handle:
        tree = ast.parse(handle.read())

    wanted = {
        node.slice.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name) and node.value.id == 'settings'
        and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str)
    }

    assert wanted, "no settings lookups found, so this test is not checking anything"
    assert wanted <= set(DEFAULTS), f"not in DEFAULTS: {sorted(wanted - set(DEFAULTS))}"


@pytest.fixture
def animatedPath(sampleImage: Image.Image, tmp_path):
    path = tmp_path / 'clip.gif'
    frames = [sampleImage.rotate(angle).convert('P') for angle in range(0, 80, 10)]
    frames[0].save(path, save_all = True, append_images = frames[1:], duration = 60, loop = 0)

    return path


@pytest.fixture(autouse = True)
def noPrompting(monkeypatch):
    """No test here may reach an `input()`; a GUI has no way to answer one."""
    def refuse(*args, **kwargs):
        raise AssertionError("The GUI path tried to prompt.")

    monkeypatch.setattr(builtins, 'input', refuse)


# ================= Layering ================

def testSessionDoesNotImportQt():
    """
    Keeps the translation testable, and keeps Qt out of anything that could be reached
    from the command line build.
    """
    with open(session.__file__, encoding = 'utf-8') as handle:
        tree = ast.parse(handle.read())

    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add(node.module or '')

    assert not any('PySide' in name or 'Qt' in name for name in names)


# ================= Reading the source ================

def testFirstFrameSurvivesTheSourceBeingClosed(samplePath):
    """
    The frame is handed out after the file it came from has been closed, so it has to be
    a copy. A lazily loaded Pillow image would raise the moment anything touched it.
    """
    image, isAnimated, frameCount, size = session.firstFrame(samplePath)

    assert image.size == size == (640, 400)
    assert not isAnimated
    assert frameCount == 1
    assert image.copy().getpixel((0, 0)) is not None


def testFirstFrameDescribesAnAnimation(animatedPath):
    image, isAnimated, frameCount, size = session.firstFrame(animatedPath)

    assert isAnimated
    assert frameCount == 8
    assert image.size == size


# ================= Tile counts ================

@pytest.mark.parametrize('mode,value,expected', [
    ('count', 40, 40),
    ('count', 99_999, 640),     # clamped to the pixels available
    ('pixels', 10, 64),         # 640 / 10
    ('pixels', 300, 3),         # rounded up, last tile takes the remainder
])
def testWidthIsResolvedTheSameWayTheCliDoesIt(mode, value, expected):
    resolved, _ = session.tileCounts(
        settings(widthMode = mode, widthValue = value), (640, 400)
    )

    assert resolved == expected


# ================= Every character mode converts ================

@pytest.mark.parametrize('overrides', [
    {},
    {'charMode': 'charset', 'charsetName': 'braille'},
    {'charMode': 'charset', 'charsetName': 'quadrants', 'dither': True},
    {'charMode': 'customRamp', 'customRamp': '@#+. '},
    {'charMode': 'pixelart', 'outputType': 'png'},
    {'colored': True, 'outputType': 'svg'},
    {'edges': True, 'threshold': 120, 'invert': True},
    {'band': (90, 170)},
    {'band': (90, 170), 'charMode': 'pixelart', 'outputType': 'png'},
    {'band': (90, 170), 'charMode': 'charset', 'charsetName': 'braille'},
])
def testEveryModePreviewsWithoutWriting(samplePath, tmp_path, overrides):
    target = tmp_path / 'never.txt'
    config = session.buildConfig(
        settings(**overrides), samplePath, target, shouldSave = False, preview = True
    )
    result = midend.execute(config)

    kind, payload = session.renderForDisplay(result, config, asPicture = True)

    assert kind == 'image'
    assert isinstance(payload, Image.Image)
    assert not target.exists()


def testTextFormatsCanBeShownEitherWay(samplePath, tmp_path):
    """The same conversion, as characters or drawn as a picture. Saving is unaffected."""
    config = session.buildConfig(
        settings(), samplePath, tmp_path / 'x.txt', shouldSave = False, preview = True
    )
    result = midend.execute(config)

    assert session.renderForDisplay(result, config, asPicture = True)[0] == 'image'

    kind, payload = session.renderForDisplay(result, config, asPicture = False)
    assert kind == 'text'
    assert len(payload.splitlines()) == config.heightCount


# ================= Animation ================

def testPreviewOfAnAnimationConvertsOneFrame(animatedPath, tmp_path):
    """Otherwise every nudge of a slider would re-convert the whole clip."""
    config = session.buildConfig(
        settings(), animatedPath, tmp_path / 'x.txt', shouldSave = False, preview = True
    )

    assert config.frameCount == session.PREVIEW_FRAMES


def testPreviewIgnoresRulesAboutWritingFiles(animatedPath, tmp_path):
    """
    A GIF cannot be saved as TXT, but it can certainly be previewed as one. The rules are
    about producing a file, and a preview does not produce one.
    """
    config = session.buildConfig(
        settings(), animatedPath, tmp_path / 'x.txt', shouldSave = False, preview = True
    )

    assert midend.execute(config) is not None


@pytest.mark.parametrize('overrides,fragment', [
    ({},                                              'holds only one'),
    ({'outputType': 'gif', 'writeFrames': True},       'already holds them all'),
])
def testSavingRefusesWhatTheCliRefuses(animatedPath, tmp_path, overrides, fragment):
    with pytest.raises(tools.Errors.GenericError) as caught:
        session.buildConfig(
            settings(**overrides), animatedPath, tmp_path / 'x.out',
            shouldSave = True, preview = False,
        )

    assert fragment in caught.value.errorMsg


def testStillImageCannotBecomeAVideo(samplePath, tmp_path):
    with pytest.raises(tools.Errors.GenericError) as caught:
        session.buildConfig(
            settings(outputType = 'mp4'), samplePath, tmp_path / 'x.mp4',
            shouldSave = True, preview = False,
        )

    assert 'single image' in caught.value.errorMsg


def testAnimationToGifIsAccepted(animatedPath, tmp_path):
    config = session.buildConfig(
        settings(outputType = 'gif', maxFrames = 3), animatedPath, tmp_path / 'x.gif',
        shouldSave = True, preview = False,
    )

    assert config.frameCount == 3


# ================= Colour never asks ================

def testColourIntoTextIsDecidedUpFront(samplePath, tmp_path):
    """
    The one setting that would otherwise reach an `input()`. `noPrompting` is what makes
    this a real assertion rather than a restatement of the value.
    """
    for wanted in (True, False):
        config = session.buildConfig(
            settings(colored = True, embedColor = wanted), samplePath,
            tmp_path / 'x.txt', shouldSave = False, preview = True,
        )
        midend.execute(config)

        assert config.embedColor is wanted


# ================= Sources are never reused ================

def testEachBuildOpensItsOwnSource(samplePath, tmp_path):
    """
    Two configs from the same settings must not share a source, because running one closes
    it. This is why the GUI rebuilds rather than caching a config between previews.
    """
    first = session.buildConfig(settings(), samplePath, tmp_path / 'a.txt',
                                shouldSave = False, preview = True)
    second = session.buildConfig(settings(), samplePath, tmp_path / 'b.txt',
                                 shouldSave = False, preview = True)

    assert first.source is not second.source

    midend.execute(first)
    midend.execute(second)


# ================= The command line it shows you ================

def parseShown(command: str, samplePath):
    """
    Runs the command the window displayed back through the real CLI parser.

    Split in non-POSIX mode because the quoting is Windows quoting: in POSIX mode a
    backslash is an escape character, and every path on the platform this runs on would
    come apart.
    """
    tokens = [token.strip('"') for token in shlex.split(command, posix = False)]

    assert tokens[:2] == ['python', 'converter.py']

    frontend.setupParser()

    return frontend.parser.parse_args(tokens[2:])


@pytest.mark.parametrize('overrides', [
    {},
    {'charMode': 'charset', 'charsetName': 'braille', 'dither': True},
    {'charMode': 'customRamp', 'customRamp': '@#+. '},
    {'charMode': 'pixelart', 'outputType': 'png'},
    {'rampSize': 10, 'invert': True, 'alpha': True},
    {'threshold': 120},
    {'band': (90, 170)},
    {'edges': True, 'edgeSensitivity': 55},
    {'widthMode': 'pixels', 'widthValue': 8, 'heightMode': 'pixels', 'heightValue': 16},
    {'colored': True, 'outputType': 'svg'},
])
def testTheShownCommandReallyIsTheConversion(samplePath, tmp_path, overrides):
    """
    The point of showing a command is that it can be trusted, so it is parsed back and the
    conversion it describes is compared against the one the window actually ran.
    """
    chosen = settings(**overrides)
    target = tmp_path / f"out.{chosen['outputType']}"

    fromWindow = session.buildConfig(chosen, samplePath, target,
                                     shouldSave = True, preview = False)

    shown = session.commandLine(chosen, samplePath, target)
    fromCli = frontend.buildConfig(parseShown(shown, samplePath))

    for field in ('widthCount', 'heightCount', 'colored', 'pixelated', 'invert', 'threshold',
                  'band', 'dither', 'edges', 'edgeSensitivity', 'alpha', 'charList',
                  'outputType', 'writeFrames'):
        assert getattr(fromCli, field) == getattr(fromWindow, field), f"{field} disagrees"

    assert fromCli.charSet.name == fromWindow.charSet.name
    assert fromCli.outputPath == fromWindow.outputPath


def testThePreviewCommandSaysItOnlyDoesOneFrame(animatedPath, tmp_path):
    shown = session.commandLine(settings(), animatedPath, tmp_path / 'x.txt', preview = True)

    assert f'--maxframes {session.PREVIEW_FRAMES}' in shown
    assert '-op' not in shown, "a preview writes nothing, so it must not show an output path"


def testTheCommandLeavesOutWhatIsNotDoingAnything():
    """A command worth copying is the short one a person would actually have typed."""
    shown = session.commandLine(settings(), pl.Path('cat.png'), pl.Path('out.txt'))

    for absent in ('-c', '-i', '-d', '--alpha', '-e', '-th', '-tb', '-g', '--frames', '-gsc'):
        assert f' {absent} ' not in f' {shown} ', f"{absent} should not appear by default"

    # Never emitted: both exist to infer counts the window always knows outright.
    assert ' -a ' not in f' {shown} ' and '-ca' not in shown


def testPathsWithSpacesAreQuoted(tmp_path):
    spacey = tmp_path / 'my pictures' / 'the cat.png'
    shown = session.commandLine(settings(), spacey, tmp_path / 'a result.txt')

    assert f'"{spacey}"' in shown
    assert shlex.split(shown, posix = False)[2].startswith('"')


def testTheColourQuestionIsCalledOutBecauseNoFlagAnswersIt():
    """
    -c with a text format makes the CLI stop and ask. The window has already decided, so
    the command on its own would not reproduce the result without a person at the keyboard.
    """
    notes = session.commandNotes(settings(colored = True, embedColor = True, outputType = 'txt'))

    assert any("'c'" in note for note in notes)
    assert not session.commandNotes(settings(colored = True, outputType = 'png'))
