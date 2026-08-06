###########################################################################
# Copyright (c) 2024-2026, Andy Pandy                                          #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################

"""
Driving a conversion from code rather than from the command line.

This is the path the GUI takes, so everything here is checked without argparse in the
picture: the config is built by hand, nothing is allowed to prompt, and the output is
collected through the callbacks instead of off stdout.
"""

import ast
import builtins

import pytest
from PIL import Image

from src import compute, config as configModule, converters, frontend, midend, sources, tools


@pytest.fixture
def animatedPath(sampleImage: Image.Image, tmp_path):
    """A six frame GIF, so the progress callback has something to count."""
    path = tmp_path / 'animated.gif'
    frames = [sampleImage.rotate(angle).convert('P') for angle in range(0, 60, 10)]
    frames[0].save(path, save_all = True, append_images = frames[1:], duration = 80, loop = 0)

    return path


@pytest.fixture
def noPrompting(monkeypatch):
    """
    Turns any attempt to read from stdin into a failure.

    A prompt reaching a GUI is a hang rather than a question, so 'it did not ask' is the
    property worth asserting, not merely 'it produced the right answer'.
    """
    def refuse(*args, **kwargs):
        raise AssertionError("The engine tried to prompt while being driven from code.")

    monkeypatch.setattr(builtins, 'input', refuse)


def buildConfig(path, tmp_path, **overrides):
    """A `Config` assembled the way a GUI assembles one, with no argparse involved."""
    settings = dict(
        source      =   sources.openSource(path),
        sourcePath  =   path,
        outputPath  =   tmp_path / 'result.txt',
        outputType  =   tools.ValidTypes.fromExtension('txt'),
        widthCount  =   40,
        heightCount =   20,
        backend     =   compute.getCpuBackend(),
        shouldSave  =   False,
    )
    settings.update(overrides)

    return configModule.Config(**settings)


# ================= The re-export still holds ================

def testFrontendStillExposesConfig():
    """
    `Config` moved out of the CLI module, but the rest of the tool refers to it as
    `frontend.Config` and should carry on being able to.
    """
    assert frontend.Config is configModule.Config
    assert frontend.DEFAULT_EDGE_SENSITIVITY == configModule.DEFAULT_EDGE_SENSITIVITY


def testConfigModuleDoesNotImportAFrontend():
    """
    The whole point of the move. If this module ever reaches back into the CLI, the GUI
    inherits argparse and the layering has quietly collapsed.

    The imports are read out of the syntax tree rather than grepped for, so that the
    module docstring can go on explaining which frontends exist without tripping this.
    """
    with open(configModule.__file__, encoding = 'utf-8') as handle:
        tree = ast.parse(handle.read())

    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or '')
            imported.update(f"{node.module}.{alias.name}" for alias in node.names)

    assert not any('frontend' in name for name in imported)
    assert not any('argparse' in name for name in imported)
    assert not any(name.startswith('gui') for name in imported)


# ================= Nothing prompts ================

@pytest.mark.parametrize('embed', [True, False])
def testEmbedColorIsHonouredWithoutAsking(samplePath, tmp_path, noPrompting, embed):
    """Colour into a text format is normally a question. Answering up front skips it."""
    config = buildConfig(samplePath, tmp_path, colored = True, embedColor = embed)
    midend.execute(config)

    assert config.embedColor is embed


def testEmbedColorAnswerIsRememberedFromAPrompt(samplePath, tmp_path, monkeypatch):
    """The CLI still asks, and still only asks once, now recording it on the same field."""
    answers = iter(['c'])
    monkeypatch.setattr(builtins, 'input', lambda *a, **k: next(answers))

    config = buildConfig(samplePath, tmp_path, colored = True)
    midend.execute(config)

    assert config.embedColor is True


def testUncoloredNeverAsks(samplePath, tmp_path, noPrompting):
    config = buildConfig(samplePath, tmp_path)
    midend.execute(config)

    assert config.embedColor is None


# ================= Callbacks ================

def testProgressCallbackCountsFrames(animatedPath, tmp_path, noPrompting):
    seen = []

    config = buildConfig(
        animatedPath, tmp_path,
        outputPath  =   tmp_path / 'result.gif',
        outputType  =   tools.ValidTypes.fromExtension('gif'),
        progress    =   lambda done, total: seen.append((done, total)),
    )
    midend.execute(config)

    assert seen, "The progress callback was never called."
    assert all(total == config.frameCount for _, total in seen)
    assert seen[-1][0] == config.frameCount
    assert [done for done, _ in seen] == sorted(done for done, _ in seen)


def testLogCallbackCapturesOutputInsteadOfPrinting(samplePath, tmp_path, capsys, noPrompting):
    lines = []

    config = buildConfig(samplePath, tmp_path, log = lines.append)
    midend.execute(config)

    assert any('Converted' in line for line in lines)
    assert capsys.readouterr().out == ""


def testWithoutALogItStillPrints(samplePath, tmp_path, capsys, noPrompting):
    """The CLI passes no callbacks, and must be entirely unaffected by their existence."""
    midend.execute(buildConfig(samplePath, tmp_path))

    assert 'Converted' in capsys.readouterr().out


# ================= Preview behaviour ================

def testShouldSaveFalseWritesNothing(samplePath, tmp_path, noPrompting):
    """How the GUI previews: run the conversion, get the result, leave the disk alone."""
    target = tmp_path / 'result.txt'
    result = midend.execute(buildConfig(samplePath, tmp_path, outputPath = target))

    assert not target.exists()
    assert isinstance(result, converters.Conversion)


def testResultCanBeRenderedToAnImageForPreview(samplePath, tmp_path, noPrompting):
    """The preview pane needs a picture, which the result converts into without a file."""
    result = midend.execute(buildConfig(samplePath, tmp_path))
    preview = converters.convertToIMG(result)

    assert isinstance(preview, Image.Image)
    assert preview.size[0] > 0 and preview.size[1] > 0


def testSourceIsSpentAfterARunSoEachConversionReopensIt(samplePath, tmp_path, noPrompting):
    """
    Pins the reason the GUI reopens the file every time rather than holding one source.

    `pConvertFrames` closes the source it was given, so reusing a config is not a thing
    callers can do. Better to have that written down here than rediscovered as a bug.
    """
    config = buildConfig(samplePath, tmp_path)
    midend.execute(config)

    with pytest.raises(Exception):
        midend.execute(config)
