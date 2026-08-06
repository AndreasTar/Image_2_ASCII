###########################################################################
# Copyright (c) 2024-2026, Andy Pandy                                          #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################

"""
Frame sources, and the animation paths that run on top of them.

Video needs an optional decoder, so those tests skip themselves when none is installed.
Everything to do with GIF, WebP and APNG must work with no extra dependency at all, and
is therefore never skipped.
"""

import shutil
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

from src import frontend, midend, sources, tools

FRAME_COUNT = 12
FRAME_DURATION_MS = 60


def hasVideoSupport() -> bool:
    for module in ('av', 'imageio_ffmpeg'):
        try:
            __import__(module)
            return True
        except ImportError:
            continue

    return shutil.which('ffmpeg') is not None


requiresVideo = pytest.mark.skipif(not hasVideoSupport(),
                                   reason = "no video decoder installed (PyAV, imageio-ffmpeg or ffmpeg)")


def buildFrames(count: int = FRAME_COUNT, size: tuple[int, int] = (96, 64)) -> list[Image.Image]:
    """A little animation of something moving, so frames are distinguishable from each other."""
    frames = []
    for index in range(count):
        image = Image.new('RGB', size, (10, 10, 20))
        draw = ImageDraw.Draw(image)
        left = 4 + index * ((size[0] - 24) // max(1, count - 1))
        draw.ellipse([left, 20, left + 18, 38], fill = (250, 200, 40))
        frames.append(image)

    return frames


@pytest.fixture
def animatedGif(tmp_path: Path) -> Path:
    path = tmp_path / 'moving.gif'
    frames = buildFrames()
    frames[0].save(path, save_all = True, append_images = frames[1:],
                   duration = FRAME_DURATION_MS, loop = 0)

    return path


@pytest.fixture
def videoFile(tmp_path: Path) -> Path:
    path = tmp_path / 'moving.mp4'
    sources.writeVideo(path, buildFrames(), 20.0)

    return path


# ================= Opening sources ================

def testStillImageIsASingleFrame(samplePath):
    with sources.openSource(samplePath) as source:
        assert isinstance(source, sources.StillSource)
        assert not source.isAnimated
        assert source.frameCount == 1
        assert len(list(source.frames())) == 1


def testAnimatedGifNeedsNoExtraDependency(animatedGif):
    """This is the promise the README makes, so it is worth asserting outright."""
    with sources.openSource(animatedGif) as source:
        assert isinstance(source, sources.PillowAnimationSource)
        assert source.isAnimated
        assert source.frameCount == FRAME_COUNT


def testAnimationFramesKeepTheirTiming(animatedGif):
    with sources.openSource(animatedGif) as source:
        frames = list(source.frames())

    assert len(frames) == FRAME_COUNT
    assert all(frame.durationMs == FRAME_DURATION_MS for frame in frames)


def testAnimationFramesAreIndependent(animatedGif):
    """
    Pillow seeks one open image rather than handing out separate frames, so anything that
    forgets to detach them ends up with every frame being the last one.
    """
    with sources.openSource(animatedGif) as source:
        frames = [np.asarray(frame.image) for frame in source.frames()]

    assert not np.array_equal(frames[0], frames[-1])


def testMissingFileIsReportedReadably(tmp_path):
    with pytest.raises(tools.Errors.GenericError, match = 'not found'):
        sources.openSource(tmp_path / 'nothing.png')


def testNonImageIsReportedReadably(tmp_path):
    path = tmp_path / 'notes.png'
    path.write_text('not a picture')

    with pytest.raises(tools.Errors.GenericError):
        sources.openSource(path)


# ================= Frame selection ================

def testFrameStepKeepsEveryNth(animatedGif):
    with sources.openSource(animatedGif, frameStep = 3) as source:
        frames = list(source.frames())

    assert len(frames) == FRAME_COUNT // 3
    assert source.selectedCount == len(frames)


def testFrameStepStretchesDurationsToKeepPlaybackSpeed(animatedGif):
    """
    Dropping two frames in three and leaving the timing alone would play three times too
    fast, so each kept frame stands in for the ones skipped after it.
    """
    with sources.openSource(animatedGif, frameStep = 3) as source:
        frames = list(source.frames())

    assert all(frame.durationMs == FRAME_DURATION_MS * 3 for frame in frames)

    totalStepped = sum(frame.durationMs for frame in frames)
    with sources.openSource(animatedGif) as source:
        totalFull = sum(frame.durationMs for frame in source.frames())

    assert totalStepped == pytest.approx(totalFull)


def testMaxFramesCapsTheCount(animatedGif):
    with sources.openSource(animatedGif, maxFrames = 5) as source:
        assert source.selectedCount == 5
        assert len(list(source.frames())) == 5


def testMaxFramesAboveTheLengthIsHarmless(animatedGif):
    with sources.openSource(animatedGif, maxFrames = 1000) as source:
        assert len(list(source.frames())) == FRAME_COUNT


def testStepAndCapCombine(animatedGif):
    with sources.openSource(animatedGif, frameStep = 2, maxFrames = 3) as source:
        assert len(list(source.frames())) == 3


# ================= Video ================

@requiresVideo
def testVideoRoundTrips(videoFile):
    with sources.openSource(videoFile) as source:
        assert isinstance(source, sources.VideoSource)
        assert source.isAnimated
        frames = list(source.frames())

    assert len(frames) > 1
    assert frames[0].image.size == (96, 64)


@requiresVideo
def testVideoFramesHaveDurationsFromTheFrameRate(videoFile):
    with sources.openSource(videoFile) as source:
        frames = list(source.frames())

    assert frames[0].durationMs == pytest.approx(1000.0 / 20.0, abs = 1.0)


@requiresVideo
def testVideoWriterProducesAPlayableFile(tmp_path):
    target = tmp_path / 'written.mp4'
    sources.writeVideo(target, buildFrames(), 15.0)

    assert target.exists() and target.stat().st_size > 0
    with sources.openSource(target) as source:
        assert len(list(source.frames())) > 1


def testMissingDecoderExplainsWhatToInstall(tmp_path, monkeypatch):
    """
    With nothing installed the message has to name every option, not just fail with an
    ImportError for whichever happened to be tried first.
    """
    path = tmp_path / 'clip.mp4'
    path.write_bytes(b'not really a video')

    monkeypatch.setattr(sources.shutil, 'which', lambda name: None)
    monkeypatch.setitem(__import__('sys').modules, 'av', None)
    monkeypatch.setitem(__import__('sys').modules, 'imageio_ffmpeg', None)

    with pytest.raises(tools.Errors.GenericError) as caught:
        sources.openSource(path)

    message = str(caught.value)
    assert 'PyAV' in message and 'imageio-ffmpeg' in message and 'ffmpeg' in message
    assert 'GIF' in message, "should point out that GIF needs nothing extra"


def testOddSizesAreRoundedForEncoding():
    """H.264 in yuv420p cannot store an odd width or height, and encoders reject them."""
    assert sources.pEvenSize((101, 65)) == (100, 64)
    assert sources.pEvenSize((100, 64)) == (100, 64)


# ================= Through the whole tool ================

@pytest.fixture(autouse = True)
def parser():
    frontend.setupParser()

    return frontend.parser


def run(inputPath, tmp_path, *args: str):
    parsed = frontend.parser.parse_args([str(inputPath), '-wc', '24', '-hc', '10', *[str(a) for a in args]])
    config = frontend.buildConfig(parsed)

    return config, midend.execute(config)


def testAnimationToGif(animatedGif, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config, frames = run(animatedGif, tmp_path, '-ot', 'gif', '-op', str(tmp_path / 'out'))

    assert len(frames) == FRAME_COUNT
    with Image.open(config.outputPath) as written:
        assert written.n_frames == FRAME_COUNT
        assert written.info['duration'] == FRAME_DURATION_MS


def testAnimationToNumberedFrames(animatedGif, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    config, _ = run(animatedGif, tmp_path, '-ot', 'txt', '--frames', '-op', str(tmp_path / 'seq'))

    folder = tmp_path / 'seq_frames'
    written = sorted(folder.glob('*.txt'))

    assert len(written) == FRAME_COUNT
    assert written[0].name == 'frame_0001.txt'
    assert written[-1].name == f'frame_{FRAME_COUNT:04d}.txt'

    # The user is told where the files are going before they appear.
    output = capsys.readouterr().out
    assert str(folder) in output
    assert 'frames as separate files' in output


def testFramesFolderIsAnnouncedBeforeWriting(animatedGif, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    run(animatedGif, tmp_path, '-ot', 'png', '--frames', '-op', str(tmp_path / 'pics'))

    output = capsys.readouterr().out
    assert output.index('Writing') < output.index('Saved'), "the warning must come first"


@requiresVideo
def testVideoInToGifOut(videoFile, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config, frames = run(videoFile, tmp_path, '-ot', 'gif', '-op', str(tmp_path / 'fromvideo'))

    assert len(frames) > 1
    with Image.open(config.outputPath) as written:
        assert written.n_frames == len(frames)


@requiresVideo
def testAnimationToVideo(animatedGif, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config, _ = run(animatedGif, tmp_path, '-ot', 'mp4', '-op', str(tmp_path / 'clip'))

    assert config.outputPath.exists() and config.outputPath.stat().st_size > 0


def testStillImageStillProducesASingleResult(samplePath, tmp_path, monkeypatch):
    """Adding animation must not have changed what a plain image does."""
    monkeypatch.chdir(tmp_path)
    config, result = run(samplePath, tmp_path, '-ot', 'txt', '-op', str(tmp_path / 'one'))

    assert not isinstance(result, list)
    assert config.outputPath.exists()


# ================= Combination rules ================

@pytest.mark.parametrize('flags,expected', [
    (['-ot', 'png'], 'frames'),
    (['-ot', 'txt'], 'frames'),
    (['-ot', 'gif', '--frames'], 'already holds them all'),
])
def testBadAnimationCombinationsExplainThemselves(animatedGif, tmp_path, flags, expected, capsys):
    with pytest.raises(SystemExit):
        run(animatedGif, tmp_path, *flags, '-op', str(tmp_path / 'x'))

    assert expected in capsys.readouterr().out


def testStillImageToVideoIsRejected(samplePath, tmp_path, capsys):
    with pytest.raises(SystemExit):
        run(samplePath, tmp_path, '-ot', 'mp4', '-op', str(tmp_path / 'x'))

    assert 'single image' in capsys.readouterr().out


def testAnimationToScreenIsAllowed(animatedGif, tmp_path, monkeypatch):
    """Playback needs no output type at all, so -p on its own must be accepted."""
    monkeypatch.chdir(tmp_path)
    parsed = frontend.parser.parse_args([str(animatedGif), '-wc', '20', '-hc', '8', '-p', '--maxframes', '2'])
    config = frontend.buildConfig(parsed)

    assert config.printToScreen and not config.shouldSave
