###########################################################################
# Copyright (c) 2024-2026, Andy Pandy                                     #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################

"""
Regenerates the examples gallery.

    python examples/generate.py

Every picture in examples/README.md comes from running the tool through this script, so
the gallery cannot drift away from what the tool actually does. Point it at a different
photograph with --source and the whole gallery rebuilds around it.

The original source photo is tall and the cat only fills the middle of it, so most runs use a crop.
The crop is worked out here rather than committed as a second file.
"""

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

EXAMPLES_DIR = Path(__file__).resolve().parent
SOURCE_DIR = EXAMPLES_DIR / 'source'
OUTPUT_DIR = EXAMPLES_DIR / 'output'

DEFAULT_SOURCE = SOURCE_DIR / 'cat.jpg'

# The subject sits in the middle of a lot of paving. These fractions of the full frame
# keep the crop meaningful if the gallery is ever rebuilt around a different photo.
CROP_FRACTIONS = (0.33, 0.075, 0.79, 0.86)


@dataclass
class Example:
    """One run: what to call it, what to say about it, and the flags to run it with."""

    name: str
    title: str
    note: str
    flags: list[str]
    cropped: bool = True
    outputType: str = 'png'
    section: str = 'Character sets'
    stdin: str = ''
    extras: dict = field(default_factory = dict)

    @property
    def outputName(self) -> str:
        return f"{self.name}.{self.outputType}"


def buildExamples() -> list[Example]:
    """Every run that ends up in the gallery."""
    return [
        # ---------------- The basics ----------------
        Example('basic', 'Default ASCII',
                'No flags beyond the grid size. The 70 character ramp, dark areas getting the '
                'heaviest characters.',
                ['-wc', '110', '-hc', '75'], section = 'The basics'),
        Example('auto', 'Automatic sizing (`-a`)',
                'Works the grid out from the image shape and the character aspect ratio, so the cat '
                'is not stretched. This is the quickest way to get a good result.',
                ['-a', '-wc', '110'], section = 'The basics'),
        Example('full-frame', 'The whole photograph',
                'Every other example here is cropped to the cat. This is the full frame, to be honest '
                'about what a busy background looks like.',
                ['-a', '-wc', '110'], cropped = False, section = 'The basics'),
        Example('colored', 'Colour (`-c`)',
                'Each cell keeps the average colour of the pixels underneath it.',
                ['-a', '-wc', '110', '-c'], outputType = 'jpg', section = 'The basics'),

        # ---------------- Character sets ----------------
        Example('charset-ascii10', 'ascii10 (`-cs ascii10`)',
                'A ten character ramp. Coarser and higher contrast than the default seventy.',
                ['-a', '-wc', '110', '-cs', 'ascii10']),
        Example('charset-blocks', 'blocks (`-cs blocks`)',
                'Unicode shading blocks. Reads as a solid image rather than as text.',
                ['-a', '-wc', '110', '-cs', 'blocks']),
        Example('charset-shades', 'shades (`-cs shades`)',
                'Partial block characters, a longer ramp than `blocks` for smoother gradients.',
                ['-a', '-wc', '110', '-cs', 'shades']),
        Example('charset-braille', 'braille (`-cs braille`)',
                'Each cell is a 2x4 grid of braille dots, so this is eight times the resolution of the '
                'same grid in ASCII. Dots go on the dark side, matching the ramps.',
                ['-a', '-wc', '110', '-cs', 'braille']),
        Example('charset-braille-dither', 'braille with dithering (`-cs braille -d`)',
                'The same run with ordered dithering. Dithering trades the clean silhouette for tone, '
                'and only earns its keep at high tile counts like this one.',
                ['-a', '-wc', '170', '-cs', 'braille', '-d']),
        Example('charset-quadrants', 'quadrants (`-cs quadrants`)',
                'Quadrant blocks, four times the resolution. Chunkier than braille and easier to read '
                'at small sizes.',
                ['-a', '-wc', '110', '-cs', 'quadrants']),
        Example('charset-halfblocks', 'halfblocks in colour (`-cs halfblocks -c`)',
                'The upper half block with a separate foreground and background colour, so one '
                'character carries two coloured pixels. Effectively a low resolution photograph.',
                ['-a', '-wc', '110', '-cs', 'halfblocks', '-c'], outputType = 'jpg'),

        # ---------------- Effects ----------------
        Example('invert', 'Invert (`-i`)',
                'Puts the heavy characters on the bright areas instead. Suits a dark background.',
                ['-a', '-wc', '110', '-i'], section = 'Effects'),
        Example('threshold', 'Threshold (`-th 120`)',
                'Two tones, split at the given brightness. Good for a stencil or sticker look.',
                ['-a', '-wc', '110', '-th', '120'], section = 'Effects'),
        Example('band', 'Band threshold (`-tb 90 170`)',
                'Keeps only the middle brightnesses and erases the rest. Unlike `-th` above it does '
                'not restyle what it keeps: every character that survives is the one the unbanded '
                'run would have put there, which is why the cat keeps its shading while the dark fur '
                'and the bright paving simply go.',
                ['-a', '-wc', '110', '-tb', '90', '170'], section = 'Effects'),
        Example('band-pixelated', 'Band threshold in pixel art (`-pix -tb 60 150`)',
                'With no characters to blank, the erased cells become properly transparent instead. '
                'Saved as PNG so the alpha survives; this page background is showing through the '
                'holes. Saving the same run as JPEG composites them onto black, since JPEG has no '
                'alpha channel.',
                ['-a', '-wc', '90', '-pix', '-c', '-tb', '60', '150'], section = 'Effects'),
        Example('edges', 'Edge detection (`-e`)',
                'Sobel edges drawn with directional characters, over the usual ramp. The strongest '
                'tenth of the image becomes edges by default.',
                ['-a', '-wc', '110', '-e'], section = 'Effects'),
        Example('edges-strong', 'More edges (`-e -et 70`)',
                'Lowering the threshold finds more edges. At 70, the strongest thirty percent.',
                ['-a', '-wc', '110', '-e', '-et', '70'], section = 'Effects'),
        Example('edges-braille', 'Edges in braille (`-cs braille -e`)',
                'With a dot based set, edge detection inks gradient strength instead of darkness, '
                'which turns the photograph into line art.',
                ['-a', '-wc', '160', '-cs', 'braille', '-e'], section = 'Effects'),
        Example('custom-ramp', 'A custom ramp (`-gs`)',
                'Any string works as a ramp, densest character first.',
                ['-a', '-wc', '110', '-gs', '@%#*+=-:. '], section = 'Effects'),
        Example('pixelated', 'Pixel art (`-pix`)',
                'Not ASCII at all: the image is shrunk to the grid and blown back up with hard edges.',
                ['-a', '-wc', '90', '-pix', '-c'], outputType = 'jpg', section = 'Effects'),

        # ---------------- Output formats ----------------
        Example('format-txt', 'Plain text (`-ot txt`)',
                'The default. One character per cell, one line per row.',
                ['-a', '-wc', '100'], outputType = 'txt', section = 'Output formats'),
        Example('format-svg', 'SVG (`-ot svg`)',
                'Vector output, so it stays sharp at any size. Runs of one colour share an element, '
                'which keeps the file reasonable.',
                ['-a', '-wc', '80', '-c'], outputType = 'svg', section = 'Output formats',
                stdin = ''),
        Example('format-xml', 'XML (`-ot xml`)',
                'Structured output for feeding into something else. Parses under any XML reader.',
                ['-a', '-wc', '60'], outputType = 'xml', section = 'Output formats'),
    ]


def cropSource(source: Path, target: Path) -> Path:
    """Crops the subject out of the middle of the source photograph."""
    with Image.open(source) as image:
        width, height = image.size
        left, top, right, bottom = CROP_FRACTIONS
        box = (int(width * left), int(height * top), int(width * right), int(height * bottom))
        image.crop(box).save(target, quality = 92)

    return target


def makeAnimation(source: Path, target: Path, frames: int = 14) -> Path:
    """
    Builds a short animated GIF by panning across the source photograph.

    Generated rather than committed, so the gallery needs only the one photo and the
    animated example still shows real picture content rather than coloured shapes.
    """
    with Image.open(source) as image:
        image = image.convert('RGB')
        width, height = image.size
        windowWidth, windowHeight = int(width * 0.42), int(height * 0.42)
        travel = width - windowWidth

        panned = []
        for index in range(frames):
            # Ease back and forth so the loop does not jump at the end.
            position = index / (frames - 1)
            offset = int(travel * (1 - abs(2 * position - 1)))
            top = int((height - windowHeight) * 0.25)
            frame = image.crop((offset, top, offset + windowWidth, top + windowHeight))
            panned.append(frame.resize((240, 240)))

    panned[0].save(target, save_all = True, append_images = panned[1:], duration = 90, loop = 0)

    return target


def runTool(inputPath: Path, outputPath: Path, flags: list[str], outputType: str, stdin: str = '') -> bool:
    """Runs the real command line tool, exactly as a user would."""
    command = [sys.executable, str(REPO_ROOT / 'converter.py'), str(inputPath),
               *flags, '-ot', outputType, '-op', str(outputPath.with_suffix(''))]

    result = subprocess.run(command, input = stdin, capture_output = True, text = True,
                            encoding = 'utf-8', errors = 'replace', cwd = str(REPO_ROOT))

    if result.returncode != 0 or not outputPath.exists():
        print(f"  FAILED: {' '.join(flags)}")
        print('  ' + (result.stdout or '').strip().replace('\n', '\n  ')[-1200:])
        return False

    return True


def commandFor(example: Example, sourceName: str) -> str:
    """The command shown in the gallery, as a user would type it."""
    flags = ' '.join(f'"{flag}"' if ' ' in flag else flag for flag in example.flags)

    return (f"python converter.py examples/source/{sourceName} {flags} "
            f"-ot {example.outputType} -op examples/output/{example.name}")


def writeGallery(examples: list[Example], results: dict, sourceName: str, animationName: str) -> None:
    """Writes examples/README.md with every run that succeeded."""
    lines = [
        '# Examples',
        '',
        'Every image on this page is produced by [generate.py](generate.py), which runs the real',
        'command line tool. Rebuild them all with:',
        '',
        '```bash',
        'python examples/generate.py',
        '```',
        '',
        'The source photograph is [source/cat.jpg](source/cat.jpg). Most runs use a crop of it,',
        'because the cat only occupies the middle of a fairly busy frame. The',
        '[full frame example](#the-whole-photograph) shows the difference.',
        '',
        '---',
        '',
    ]

    order = ['The basics', 'Character sets', 'Effects', 'Output formats', 'Animation']
    for section in order:
        chosen = [e for e in examples if e.section == section and results.get(e.name)]
        if not chosen:
            continue

        lines.append(f'## {section}')
        lines.append('')

        for example in chosen:
            lines.append(f'### {example.title}')
            lines.append('')
            lines.append(example.note)
            lines.append('')
            lines.append('```bash')
            lines.append(commandFor(example, sourceName))
            lines.append('```')
            lines.append('')

            if example.outputType in ('png', 'jpg', 'gif', 'svg'):
                lines.append(f'<img src="output/{example.outputName}" alt= "{example.title}" width="400">')
            else:
                lines.append(f'[View the output file](output/{example.outputName})')
                preview = (OUTPUT_DIR / example.outputName).read_text(encoding = 'utf-8').splitlines()
                if example.outputType == 'txt':
                    lines.append('')
                    lines.append('<details><summary>Show the first lines</summary>')
                    lines.append('')
                    lines.append('```')
                    lines.extend(preview[:22])
                    lines.append('```')
                    lines.append('')
                    lines.append('</details>')

            lines.append('')

    lines.append('## Animation')
    lines.append('')
    lines.append('Animated GIFs, WebP and APNG need no extra dependency at all. Video files need a')
    lines.append('decoder installed; see the main README.')
    lines.append('')
    lines.append('```bash')
    lines.append(f'python converter.py examples/source/{animationName} -a -wc 64 '
                 f'-cs blocks -c -ot gif -op examples/output/animation')
    lines.append('```')
    lines.append('')
    lines.append('<img src="output/animation.gif" alt= "Animated example" width="400">')
    lines.append('')
    lines.append('The same input can also be played straight in the terminal with `-p`, written as one')
    lines.append('file per frame with `--frames`, or re-encoded to a video with `-ot mp4`.')
    lines.append('')

    (EXAMPLES_DIR / 'README.md').write_text('\n'.join(lines), encoding = 'utf-8')


def main() -> int:
    parser = argparse.ArgumentParser(description = 'Regenerates the examples gallery.')
    parser.add_argument('--source', type = Path, default = DEFAULT_SOURCE,
                        help = 'The photograph to build the gallery from.')
    args = parser.parse_args()

    if not args.source.exists():
        print(f"Source image not found -> {args.source}")
        return 1

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents = True)

    working = EXAMPLES_DIR / '.working'
    working.mkdir(exist_ok = True)

    cropped = cropSource(args.source, working / 'cropped.jpg')
    animation = makeAnimation(args.source, working / 'panned.gif')

    examples = buildExamples()
    results = {}

    print(f"Generating {len(examples)} examples from {args.source.name}...")
    for example in examples:
        inputPath = cropped if example.cropped else args.source
        outputPath = OUTPUT_DIR / example.outputName
        results[example.name] = runTool(inputPath, outputPath, example.flags,
                                        example.outputType, example.stdin)
        print(f"  {'ok  ' if results[example.name] else 'FAIL'} {example.name}")

    animationOut = OUTPUT_DIR / 'animation.gif'
    animationOk = runTool(animation, animationOut,
                          ['-a', '-wc', '64', '-cs', 'blocks', '-c'], 'gif')
    print(f"  {'ok  ' if animationOk else 'FAIL'} animation")

    writeGallery(examples, results, args.source.name, 'cat.jpg')
    shutil.rmtree(working, ignore_errors = True)

    succeeded = sum(1 for value in results.values() if value) + (1 if animationOk else 0)
    total = len(examples) + 1
    print(f"\n{succeeded} of {total} examples generated into {OUTPUT_DIR}")
    print(f"Gallery written to {EXAMPLES_DIR / 'README.md'}")

    return 0 if succeeded == total else 1


if __name__ == '__main__':
    raise SystemExit(main())
