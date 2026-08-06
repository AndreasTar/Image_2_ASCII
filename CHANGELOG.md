# Changelog

All notable changes to this project are documented here.
This project follows [Semantic Versioning](https://semver.org/).

## [2.1.0]

### Added

- **`-tb` / `--thresholdband`, a two-ended threshold.** Give it a low and a high brightness
  and everything outside that range is erased entirely (a blank character, or a transparent
  block with `-pix`) while everything inside is left exactly as it would have been with no
  threshold at all. That is what separates it from `-th`, which rewrites every value it is
  given. Sub-cell sets are blanked with their own empty character rather than a space, since
  a space in a braille run is a hole of the wrong width, and banded pixel art saved as JPEG
  is composited onto black because JPEG has no alpha channel.
- **The window logs the command line it just ran**, for previews as well as saves, so what
  it did can be read, copied and run from a terminal as-is. Settings the panel has greyed out
  never reach the command, and the one thing no flag can express (the answer to the colour
  question `-c` asks of a text format) is spelled out underneath.
- **[THIRD-PARTY.md](THIRD-PARTY.md)**, naming every dependency and its licence, and shipped
  inside both downloads. The windowed one also carries the full LGPL-3.0 and GPL-3.0 texts
  beside the executable, which distributing Qt in a binary requires and which the PySide6
  wheels do not themselves provide.
- **A Windows version resource on both executables**, so Explorer's Properties tab names
  them, their author and their version instead of reporting 0.0.0.0 with no author at all.
  Generated from `tools.APP_VERSION` at build time, so what Explorer shows and what
  `--version` prints cannot disagree. It does not quieten SmartScreen, only a signing
  certificate does that, but it does let a downloaded file say what it is.
- **Two gallery examples for the band threshold**, one showing what it does to characters
  next to the `-th` example it is easily confused with, and one showing the transparency it
  punches through pixel art. The gallery is now 24 runs.
- **A note in the README about the SmartScreen warning.** Both executables are unsigned, so
  Windows reports them as unrecognised and some antivirus products quarantine them outright.
  That is a known false positive affecting PyInstaller programs generally rather than
  anything about this one, and users deserve to be told before they meet it rather than
  after.

### Fixed

- **The two preview panes only stayed in step for pixel art.** They shared a view transform,
  which needs both pictures to be the same size, and pixel art was the only output for which
  that was true. They now share the visible *region* as a proportion of each picture, so a
  60 character conversion tracks the 2000 pixel photograph it came from.
- **Fit left the result undersized** whenever it was not the same shape as the source, for
  the same reason. Each pane is now fitted to its own contents.
- **The text preview overflowed its pane.** Its font is now sized so the whole grid fits,
  found by measuring at each candidate size rather than by scaling from one reference, since
  a font hints its glyphs onto whole pixels and at small sizes the rounding is enough to push
  the text back over the edge.
- **Zoom had no usable limits.** Both ends are now measured against the scale at which the
  picture fits its pane, which is the only thing that means anything across two views showing
  pictures of very different sizes.
- **Colour appeared to do nothing** with a text format, because TXT and XML only carry it
  when it is written into them. The panel now says so instead of leaving it a mystery.

## [2.0.0]

The major version is for what the project *is* rather than for anything that broke: this is
no longer a command line tool, it is an engine with two frontends on it, shipped as two
separate downloads. Every flag, output format and conversion behaves exactly as it did in
1.2.0, and no command line that worked before needs changing.

### Added

- **A windowed version.** `python converter_gui.py` opens a graphical frontend with a control
  for every flag, the source and result side by side on a shared zoom, and the conversion
  re-running as settings change. Nothing is written until a destination is chosen, so trying
  settings out costs nothing. Built with PySide6, which is a dependency of the window only:
  the command line version still installs and runs from `requirements.txt` alone.
  - The character sets, output formats, ramp sizes and compute backends in its dropdowns are
    read out of the engine rather than listed again, so adding one to `tools` puts it in the
    window with no GUI change at all.
  - Text formats can be shown either as the characters that will be written or drawn as a
    picture, so the result can be compared against the source it came from. The saved file is
    the same either way.
- **A second executable, built separately from the first.** `Image2AsciiGUI.spec` builds the
  windowed version as a folder of about 134 MB; `Image2Ascii.spec` continues to build the
  command line one as a single file of about 28 MB, with no interface code and no Qt in it.
  Neither download carries the other's weight. Shared build settings live in
  [buildcommon.py](buildcommon.py) so the two cannot drift apart.
- `requirements-gui.txt`, for the windowed version's dependencies.

### Changed

- **`Config` moved from `frontend` into a new `src/config.py`**, along with the rules about
  which setting combinations can produce a file and the choosing of a character set. Both
  frontends now share one definition of each, rather than the GUI reimplementing what the
  command line already knew. `frontend.Config` still resolves.
- **The midend no longer insists on a terminal.** It reports through optional `progress` and
  `log` callbacks on the config, falling back to printing when they are not set, and the
  question it used to ask with `input()` when `-c` met a text output format can now be
  answered up front with `embedColor`. The command line behaves exactly as before; a caller
  with no terminal to prompt through no longer hangs.

### Notes

- PySide6 is used under the LGPL. The windowed version is built as a folder rather than a
  single file so that the Qt libraries beside the executable stay replaceable, which is what
  that licence asks of a binary distribution. This project's own source remains BSD licensed.

## [1.2.0]

### Added

- **Animated input.** Animated GIF, WebP and APNG are read with no extra dependency at all,
  since Pillow already handles them. Video files (mp4, mov, avi, webm, mkv and friends) work
  too when a decoder is available: PyAV, imageio-ffmpeg or an `ffmpeg` binary on the PATH,
  tried in that order. None of them are required, and none are in `requirements.txt`.
- **Four ways to write an animation**: `-ot gif` for an animated GIF (no dependency),
  `-p` to play it in the terminal at the source's own timing, `--frames` to write one
  numbered file per frame into a subfolder, and `-ot mp4` to re-encode it as a video.
- `--maxframes`, `--framestep` and `--fps` for controlling how much of a clip is converted
  and how fast the result plays. Stepping stretches each kept frame's duration so playback
  speed is preserved.
- **`-cs` / `--charset`, with built-in character sets.** `ascii70`, `ascii10`, `blocks` and
  `shades` are ordinary ramps. `braille` (2x4 dots per cell, eight times the resolution),
  `quadrants` (2x2, four times) and `halfblocks` (two colours per cell) split each cell into
  sub-cells and pack the result into one character.
- `-d` / `--dither`, ordered dithering for the dot based sets.
- **Coloured terminal output.** `-p` together with `-c` writes 24-bit ANSI colour, with runs
  of one colour collapsed into a single escape sequence.
- **An examples gallery** in [examples/](examples/README.md), with 22 runs covering every
  character set, effect and output format. It is produced by
  [examples/generate.py](examples/generate.py), which runs the real tool, so it cannot drift
  away from actual behaviour.

### Changed

- Block and shading characters are drawn as the exact rectangles they are defined to be
  rather than from a font. Fonts draw them inside the em box while a cell is taller than
  that, which left a visible seam between every row. Drawing them directly also means those
  sets need no symbol font installed.
- The image writer picks a font by checking it actually contains the characters being drawn.
  Most fixed width fonts, Consolas and Courier New included, have no braille glyphs and
  quietly substitute a `.notdef` box, so a braille render came out as a neat grid of empty
  rectangles.
- Configuration now carries a frame source rather than a single image, so a still picture is
  simply a one frame animation and there is one code path rather than two.
- The colour prompt for text formats is asked once per run rather than once per frame.

### Fixed

- **Video conversion silently dropped its first frame**, then failed outright on short
  clips. The frame size was being measured by decoding a frame, and a video decodes in one
  direction only, so that frame never reached the conversion.
- Edge detection with a dot based character set inked every dot on an image with no edges
  in it, because any percentile of an all-zero gradient is also zero.
- `sys.stdout` is switched to UTF-8 at start-up, and virtual terminal processing is enabled
  on Windows. Without the first, printing braille or block characters raised
  `UnicodeEncodeError` and killed the run on a default Windows console; without the second,
  colour output appeared as raw escape codes.

## [1.1.0]

### Added

- **Optional GPU acceleration** via `-g` / `--gpu`, backed by either CuPy or a GPU build of
  PyTorch. Neither is required, neither is installed by default, and neither is imported
  unless the flag is actually used. Without one, `--gpu` explains why and uses the CPU.
- `-i` / `--invert`, to put the dense characters on the bright areas instead of the dark ones.
- `-th` / `--threshold`, to collapse the image to two tones at a given brightness cutoff.
- `-gs` / `--grayscale`, to supply a custom character ramp instead of the two built-in ones.
- `-e` / `--edges` and `-et` / `--edgethreshold`, Sobel edge detection drawn with directional
  characters (`|`, `/`, `-`, `\`).
- `-ca` / `--charaspect`, to correct for character cells being taller than they are wide.
- `-p` / `--print`, to write the result to the screen. Nothing is saved unless `-op` is also given.
- `--alpha`, to flatten transparent areas onto black instead of ignoring the alpha channel.
- A test suite, run with `pytest`. The conversion core is checked against the original
  tile-at-a-time implementation, which is kept in `tests/reference.py` for that purpose.
- A PyInstaller spec, for building a standalone executable that needs no Python installed.

### Changed

- **`-a` / `--auto` now works.** It was previously advertised but did nothing. It fills in
  whichever tile counts were not given, from the image aspect ratio, the terminal size and
  the character aspect ratio, instead of prompting for them.
- **The conversion core is vectorised.** It previously cropped and averaged one tile at a
  time in Python; it now reduces the whole grid at once. Measured on a 3840x2160 image:
  an 80,000 tile grid went from 2.6 s to 0.11 s, and a 320,000 tile grid from 10.1 s to
  0.20 s. The bigger the output, the bigger the difference.
- Raster output is assembled from a glyph atlas rather than one draw call per cell, and
  the character cell is now measured from the font instead of being assumed to be 12px.
- SVG output groups runs of same-coloured characters into a single `<tspan>` instead of
  emitting one per character, which makes the files dramatically smaller.
- XML output has a declaration and a root element, and a grayscale row is written as one
  element rather than one element per character.
- The colour prompt for `.txt` and `.xml` output now re-asks on an unrecognised answer.
- Configuration is a proper object per run, instead of being written onto a shared class.

### Fixed

- **Colours were scrambled on any non-square output.** The colour of each cell was looked
  up with the wrong row stride, so it only lined up when the grid was exactly square.
- **XML output was not valid XML.** Character elements were never closed, there was no root
  element, and the default 70-character ramp contains `&`, `<` and `>`, which were written
  out raw. Plain (non-coloured) XML output contained no markup at all.
- **`--colored` crashed on any input that was not already RGB**, including palette PNGs,
  grayscale images and RGBA images.
- **Image output was written through a text file handle** opened over the same path.
- **An invalid `--grayscalecount` raised `NameError`** instead of reporting the problem.
- The colour prompt accepted any substring of `tce`, so answering `tc` passed validation,
  matched no branch, and silently wrote unconverted output.
- Output names taken from the input file assumed a three letter extension, so `photo.jpeg`
  became `photo` rather than `photo`, mangling anything longer or shorter.
- The last entry of every word list used to generate random output names was unreachable.
- `--colored` combined with `--pixelated` computed three full colour passes that were then
  thrown away.
- Finding the divisors of the image size is now O(sqrt n) rather than O(n).

### Notes

- Tile averages are no longer truncated to whole numbers before a character is chosen, so
  a cell may land one step further along the ramp than it did in 1.0.0.
- Pillow's `BOX` resampling is deliberately not used for the tile averaging despite being
  faster: on some image and grid size combinations it is off by around 11 grayscale
  levels, which is several characters' worth. See `tests/test_backend.py`.

## [1.0.0]

- Conversion to pixelart, via `-pix`.
- Output file saved to a given path with a chosen name.
- Conversion logic separated from the input/output controller.
- First release, with semver and tags set up.
