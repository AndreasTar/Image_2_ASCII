###########################################################################
# Copyright (c) 2024-2026, Andy Pandy                                          #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################

"""
Where frames come from, and where video frames go.

A still image is one frame, an animated GIF is several, a video is a great many. The rest
of the tool does not care which, so everything arrives through one `FrameSource`.

Animated GIF, WebP and APNG cost nothing extra: Pillow already reads them. Video is the
only thing here that needs a decoder, and following the same rule as `compute`, none of
the candidates are imported until a video is actually opened, and none of them appear in
requirements.txt. Reading and writing video share those dependencies, which is why the
encoder lives in this module too.
"""

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from PIL import Image, ImageSequence, UnidentifiedImageError

from src import tools

# Containers we hand to a video decoder rather than to Pillow.
VIDEO_SUFFIXES = ('.mp4', '.mov', '.avi', '.webm', '.mkv', '.m4v', '.mpg', '.mpeg', '.wmv', '.flv')

# Frame delay used when an animation does not declare one. Matches Pillow's own fallback.
DEFAULT_FRAME_DURATION_MS = 100.0

INSTALL_HINT = ("To convert video, install one of:\n"
                "\t  pip install av\n"
                "\t  pip install imageio-ffmpeg\n"
                "\tor put an 'ffmpeg' binary on your PATH.\n"
                "\tAnimated GIF, WebP and APNG need none of these.")


@dataclass
class Frame:
    """One frame, and how long it should be shown for."""

    image: Image.Image
    durationMs: float = DEFAULT_FRAME_DURATION_MS


class FrameSource:
    """
    A sequence of frames, however they happen to be stored.

    Subclasses provide `pReadFrames`; selection by `--framestep` and `--maxframes` is
    applied here so every source honours them identically.
    """

    path: Path
    frameCount: int
    size: tuple[int, int]
    isAnimated: bool = False

    def __init__(self, path: Path, frameStep: int = 1, maxFrames: int | None = None) -> None:
        self.path = path
        self.pFrameStep = max(1, frameStep)
        self.pMaxFrames = maxFrames

    @property
    def selectedCount(self) -> int:
        """How many frames will actually be converted, after stepping and capping."""
        stepped = (self.frameCount + self.pFrameStep - 1) // self.pFrameStep

        return min(stepped, self.pMaxFrames) if self.pMaxFrames else stepped

    def frames(self) -> Iterator[Frame]:
        """Yields the frames to convert, honouring the step and cap."""
        taken = 0
        for index, frame in enumerate(self.pReadFrames()):
            if index % self.pFrameStep:
                continue
            if self.pMaxFrames is not None and taken >= self.pMaxFrames:
                return

            # Stepping means each kept frame stands in for the ones skipped after it.
            frame.durationMs *= self.pFrameStep
            taken += 1

            yield frame

    def pReadFrames(self) -> Iterator[Frame]:
        """
        --- Private method! ---\n
        Every frame in the file, before selection.
        """
        raise tools.Errors.Unimplemented()

    def close(self) -> None:
        return None

    def __enter__(self) -> 'FrameSource':
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


class StillSource(FrameSource):
    """A single image. This is what the tool did before it understood animation."""

    isAnimated = False

    def __init__(self, path: Path, image: Image.Image, **kwargs) -> None:
        super().__init__(path, **kwargs)
        self.pImage = image
        self.frameCount = 1
        self.size = image.size

    def pReadFrames(self) -> Iterator[Frame]:
        yield Frame(self.pImage, 0.0)

    def close(self) -> None:
        self.pImage.close()


class PillowAnimationSource(FrameSource):
    """
    An animated GIF, WebP or APNG.

    Pillow seeks the one open image rather than handing out independent frames, so each
    frame is converted to RGB on the way out, which also detaches it from the file.
    """

    isAnimated = True

    def __init__(self, path: Path, image: Image.Image, **kwargs) -> None:
        super().__init__(path, **kwargs)
        self.pImage = image
        self.frameCount = getattr(image, 'n_frames', 1)
        self.size = image.size

    def pReadFrames(self) -> Iterator[Frame]:
        for frame in ImageSequence.Iterator(self.pImage):
            duration = float(frame.info.get('duration') or DEFAULT_FRAME_DURATION_MS)

            yield Frame(frame.convert('RGB'), duration)

    def close(self) -> None:
        self.pImage.close()


class VideoSource(FrameSource):
    """
    A video file, decoded by whichever optional backend is installed.

    The backend is resolved once when the source is opened, so a missing decoder is
    reported before any conversion work starts rather than partway through a long clip.
    """

    isAnimated = True

    def __init__(self, path: Path, reader: 'PVideoReader', **kwargs) -> None:
        super().__init__(path, **kwargs)
        self.pReader = reader
        self.frameCount = reader.frameCount
        self.fps = reader.fps
        self.decoderName = reader.name
        # Taken from the stream header rather than by decoding a frame. A video decodes
        # in one direction only, so peeking at a frame to measure it would consume it.
        self.size = reader.size

    def pReadFrames(self) -> Iterator[Frame]:
        duration = 1000.0 / self.fps if self.fps else DEFAULT_FRAME_DURATION_MS
        for image in self.pReader.read():
            yield Frame(image, duration)

    def close(self) -> None:
        self.pReader.close()


def openSource(path: Path, frameStep: int = 1, maxFrames: int | None = None) -> FrameSource:
    """
    Opens whatever is at `path` as a sequence of frames.

    Videos go to a decoder; everything else goes to Pillow, which then tells us whether it
    is animated. Raises tools.Errors.GenericError with something readable on failure.
    """
    if path.suffix.lower() in VIDEO_SUFFIXES:
        return VideoSource(path, pOpenVideoReader(path), frameStep = frameStep, maxFrames = maxFrames)

    try:
        image = Image.open(path)
    except FileNotFoundError:
        raise tools.Errors.GenericError(f"File path was not found -> {path}")
    except UnidentifiedImageError:
        raise tools.Errors.GenericError(
            f"File is not an image Pillow can read -> {path}\n"
            f"\tIf this is a video, it needs one of the supported extensions: {', '.join(VIDEO_SUFFIXES)}"
        )
    except OSError as e:
        raise tools.Errors.GenericError(f"Could not read the input file -> {path}\n\t{e}")

    if getattr(image, 'is_animated', False):
        return PillowAnimationSource(path, image, frameStep = frameStep, maxFrames = maxFrames)

    return StillSource(path, image, frameStep = frameStep, maxFrames = maxFrames)


# ================= Video decoding ================

class PVideoReader:
    """
    --- Private class! ---\n
    A decoder that can hand back RGB frames. One subclass per optional backend.
    """

    name: str
    frameCount: int
    fps: float
    size: tuple[int, int]

    def read(self) -> Iterator[Image.Image]:
        raise tools.Errors.Unimplemented()

    def close(self) -> None:
        return None


class PPyAvReader(PVideoReader):
    """--- Private class! --- Decodes with PyAV, which bundles its own ffmpeg libraries."""

    name = 'PyAV'

    def __init__(self, av: Any, path: Path) -> None:
        self.pAv = av
        self.pContainer = av.open(str(path))
        stream = self.pContainer.streams.video[0]
        stream.thread_type = 'AUTO'
        self.pStream = stream
        self.size = (stream.width, stream.height)
        self.fps = float(stream.average_rate) if stream.average_rate else 30.0
        # frames is 0 for streams that do not declare a count; fall back to duration.
        self.frameCount = stream.frames or int((stream.duration or 0) * float(stream.time_base or 0) * self.fps) or 1

    def read(self) -> Iterator[Image.Image]:
        for frame in self.pContainer.decode(self.pStream):
            yield frame.to_image()

    def close(self) -> None:
        self.pContainer.close()


class PImageioReader(PVideoReader):
    """--- Private class! --- Decodes with imageio-ffmpeg, which ships an ffmpeg binary."""

    name = 'imageio-ffmpeg'

    def __init__(self, imageio: Any, path: Path) -> None:
        self.pReader = imageio.read_frames(str(path))
        meta = self.pReader.__next__()                  # first yield is the metadata
        self.fps = float(meta.get('fps') or 30.0)
        self.pSize = meta['size']
        self.size = tuple(meta['size'])
        duration = float(meta.get('duration') or 0.0)
        self.frameCount = int(duration * self.fps) or 1

    def read(self) -> Iterator[Image.Image]:
        width, height = self.pSize
        for data in self.pReader:
            yield Image.frombytes('RGB', (width, height), data)

    def close(self) -> None:
        self.pReader.close()


class PFfmpegReader(PVideoReader):
    """
    --- Private class! ---\n
    Decodes by piping raw RGB out of an ffmpeg binary already on the PATH.

    The zero dependency option: no Python package involved, just the program most people
    doing anything with video already have installed.
    """

    name = 'ffmpeg'

    def __init__(self, path: Path) -> None:
        self.pPath = path
        self.pWidth, self.pHeight, self.fps, self.frameCount = pProbeWithFfprobe(path)
        self.size = (self.pWidth, self.pHeight)
        self.pProcess = None

    def read(self) -> Iterator[Image.Image]:
        command = [shutil.which('ffmpeg'), '-v', 'error', '-i', str(self.pPath),
                   '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']
        self.pProcess = subprocess.Popen(command, stdout = subprocess.PIPE, stderr = subprocess.DEVNULL)

        frameBytes = self.pWidth * self.pHeight * 3
        while True:
            data = self.pProcess.stdout.read(frameBytes)
            if len(data) < frameBytes:
                return

            yield Image.frombytes('RGB', (self.pWidth, self.pHeight), data)

    def close(self) -> None:
        if self.pProcess is not None:
            self.pProcess.stdout.close()
            self.pProcess.terminate()
            self.pProcess.wait(timeout = 5)


def pProbeWithFfprobe(path: Path) -> tuple[int, int, float, int]:
    """
    --- Private method! ---\n
    Asks ffprobe for the dimensions, frame rate and length of a video.
    """
    ffprobe = shutil.which('ffprobe')
    if ffprobe is None:
        raise tools.Errors.GenericError("Found ffmpeg but not ffprobe; both are needed to read video.")

    command = [ffprobe, '-v', 'error', '-select_streams', 'v:0',
               '-show_entries', 'stream=width,height,avg_frame_rate,nb_frames,duration',
               '-of', 'default=noprint_wrappers=1', str(path)]
    output = subprocess.run(command, capture_output = True, text = True, check = False).stdout

    fields = dict(line.split('=', 1) for line in output.splitlines() if '=' in line)

    try:
        width, height = int(fields['width']), int(fields['height'])
    except (KeyError, ValueError):
        raise tools.Errors.GenericError(f"ffprobe could not read the dimensions of -> {path}")

    rate = fields.get('avg_frame_rate', '30/1')
    numerator, _, denominator = rate.partition('/')
    fps = float(numerator) / float(denominator) if denominator and float(denominator) else 30.0

    count = fields.get('nb_frames', 'N/A')
    if count.isdigit():
        frameCount = int(count)
    else:
        try:
            frameCount = int(float(fields.get('duration', 0)) * fps) or 1
        except ValueError:
            frameCount = 1

    return width, height, fps, frameCount


def pOpenVideoReader(path: Path) -> PVideoReader:
    """
    --- Private method! ---\n
    Resolves a video decoder, trying each optional backend in turn.

    Reports every backend it tried and why each one was unavailable, rather than a bare
    ImportError for whichever happened to be checked first.
    """
    if not path.exists():
        raise tools.Errors.GenericError(f"File path was not found -> {path}")

    reasons = []

    try:
        import av
        return PPyAvReader(av, path)
    except ImportError:
        reasons.append("PyAV is not installed")
    except Exception as e:
        reasons.append(f"PyAV could not open the file ({e})")

    try:
        import imageio_ffmpeg
        return PImageioReader(imageio_ffmpeg, path)
    except ImportError:
        reasons.append("imageio-ffmpeg is not installed")
    except Exception as e:
        reasons.append(f"imageio-ffmpeg could not open the file ({e})")

    if shutil.which('ffmpeg') is None:
        reasons.append("no 'ffmpeg' binary on the PATH")
    else:
        try:
            return PFfmpegReader(path)
        except tools.Errors.GenericError:
            raise
        except Exception as e:
            reasons.append(f"ffmpeg could not open the file ({e})")

    listed = '\n'.join(f"\t- {reason}" for reason in reasons)
    raise tools.Errors.GenericError(f"No video decoder is available:\n{listed}\n\n\t{INSTALL_HINT}")


# ================= Video encoding ================

def writeVideo(path: Path, frames: list[Image.Image], fps: float) -> str:
    """
    Encodes finished frames into a video file.

    Uses the same optional backends as decoding, so a machine that can read video can
    write it. Returns the name of the backend that did the work, for reporting.
    """
    if not frames:
        raise tools.Errors.GenericError("There are no frames to write!")

    reasons = []

    try:
        import av
        return pWriteWithPyAv(av, path, frames, fps)
    except ImportError:
        reasons.append("PyAV is not installed")

    try:
        import imageio_ffmpeg
        return pWriteWithImageio(imageio_ffmpeg, path, frames, fps)
    except ImportError:
        reasons.append("imageio-ffmpeg is not installed")

    if shutil.which('ffmpeg') is not None:
        return pWriteWithFfmpeg(path, frames, fps)
    reasons.append("no 'ffmpeg' binary on the PATH")

    listed = '\n'.join(f"\t- {reason}" for reason in reasons)
    raise tools.Errors.GenericError(
        f"No video encoder is available:\n{listed}\n\n\t{INSTALL_HINT}\n"
        f"\tYou can also write the animation as a GIF with -ot gif, which needs nothing extra."
    )


def pWriteWithPyAv(av: Any, path: Path, frames: list[Image.Image], fps: float) -> str:
    """--- Private method! --- Encodes H.264 with PyAV."""
    width, height = pEvenSize(frames[0].size)

    with av.open(str(path), mode = 'w') as container:
        stream = container.add_stream('libx264', rate = round(fps) or 1)
        stream.width, stream.height = width, height
        stream.pix_fmt = 'yuv420p'

        for image in frames:
            resized = image if image.size == (width, height) else image.resize((width, height))
            packet = stream.encode(av.VideoFrame.from_image(resized))
            container.mux(packet)

        container.mux(stream.encode())

    return 'PyAV'


def pWriteWithImageio(imageio: Any, path: Path, frames: list[Image.Image], fps: float) -> str:
    """--- Private method! --- Encodes with the ffmpeg binary imageio-ffmpeg ships."""
    width, height = pEvenSize(frames[0].size)
    writer = imageio.write_frames(str(path), (width, height), fps = fps, macro_block_size = 1)
    writer.send(None)

    for image in frames:
        resized = image if image.size == (width, height) else image.resize((width, height))
        writer.send(resized.convert('RGB').tobytes())

    writer.close()

    return 'imageio-ffmpeg'


def pWriteWithFfmpeg(path: Path, frames: list[Image.Image], fps: float) -> str:
    """--- Private method! --- Encodes by piping raw RGB into an ffmpeg binary."""
    width, height = pEvenSize(frames[0].size)
    command = [shutil.which('ffmpeg'), '-v', 'error', '-y',
               '-f', 'rawvideo', '-pix_fmt', 'rgb24',
               '-s', f'{width}x{height}', '-r', str(fps), '-i', '-',
               '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(path)]

    process = subprocess.Popen(command, stdin = subprocess.PIPE, stderr = subprocess.DEVNULL)
    for image in frames:
        resized = image if image.size == (width, height) else image.resize((width, height))
        process.stdin.write(resized.convert('RGB').tobytes())

    process.stdin.close()
    if process.wait() != 0:
        raise tools.Errors.GenericError(f"ffmpeg failed while writing -> {path}")

    return 'ffmpeg'


def pEvenSize(size: tuple[int, int]) -> tuple[int, int]:
    """
    --- Private method! ---\n
    Rounds a size down to even numbers.

    H.264 in yuv420p stores colour at half resolution in both directions, so it cannot
    represent an odd width or height, and encoders reject them outright.
    """
    width, height = size

    return width - width % 2, height - height % 2
