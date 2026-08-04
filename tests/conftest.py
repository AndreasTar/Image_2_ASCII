###########################################################################
# Copyright (c) 2024, Andy Pandy                                          #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################

import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Grid shapes worth checking: square, wide, tall, prime sided, one that divides the image
# evenly and one that very much does not, plus the degenerate single tile.
GRID_CASES = [(80, 25), (113, 37), (7, 3), (1, 1), (64, 40), (199, 101)]


@pytest.fixture(scope = 'session')
def sampleImage() -> Image.Image:
    """A 640x400 RGB picture with gradients, hard edges and diagonals in it."""
    width, height = 640, 400
    image = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(image)

    for x in range(width):
        draw.line([(x, 0), (x, height)], fill = (int(255 * x / width), 60, 255 - int(255 * x / width)))

    draw.ellipse([60, 60, 300, 300], fill = (250, 250, 250), outline = (0, 0, 0), width = 6)
    draw.rectangle([360, 80, 600, 280], fill = (20, 20, 20), outline = (255, 255, 0), width = 5)
    draw.line([(360, 320), (600, 360)], fill = (255, 255, 255), width = 7)
    draw.polygon([(120, 340), (240, 340), (180, 395)], fill = (0, 0, 0))

    return image


@pytest.fixture(scope = 'session')
def grayImage(sampleImage: Image.Image) -> Image.Image:
    return sampleImage.convert('L')


@pytest.fixture(scope = 'session')
def noiseImage() -> Image.Image:
    """Pure noise, which has no structure for any tile boundary to hide behind."""
    pixels = np.random.default_rng(1234).integers(0, 256, (257, 389), dtype = np.uint8)

    return Image.fromarray(pixels, 'L')


@pytest.fixture
def samplePath(sampleImage: Image.Image, tmp_path: Path) -> Path:
    path = tmp_path / 'sample.png'
    sampleImage.save(path)

    return path
