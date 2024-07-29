###########################################################################
# Copyright (c) 2024, Andy Pandy                                          #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################

from enum import Enum
import numpy as np


class Errors:
    class GenericError(Exception):

        error_msg = "Generic error message!"

        def __init__(self, error_msg = error_msg, *args: object) -> None:
            self.error_msg = error_msg

            super().__init__(self.error_msg)
    
    class UNIMPLEMENTED(GenericError):

        def __init__(self, *args: object) -> None:
            super().__init__("FUNCTION IS NOT IMPLEMENTED!")

    class VariableNotInitialisedError(GenericError):

        var_name = ""
        error_msg = f"Value was accessed before being initialised!"

        def __init__(self, var_name: str, error_msg = error_msg, *args: object) -> None:
            self.var_name = var_name
            self.errorMsg = error_msg + f"\n\t\tVariable Name -> {var_name}"

            super().__init__(self.error_msg)

    class VariableInvalidValueError(GenericError):

        var_name = ""
        var_value = None
        error_msg = "Variable has an invalid value!"

        def __init__(self, var_name: str, var_value, error_msg = error_msg, *args: object) -> None:
            self.var_name = var_name
            self.var_value = var_value
            self.error_msg = error_msg + f"\n\t\tVariable Name -> {var_name}\n\t\tVariable Value -> {var_value}"

            super().__init__(self.error_msg)


class ValidTypes(Enum):
    TXT = 0,
    JPG = 1,
    PNG = 2,
    XML = 3,
    SVG = 4

    @classmethod
    def asList(self):
        return [v.name.lower() for v in self]



# gray scale level values from: 
# http://paulbourke.net/dataformats/asciiart/
# for Courier font, aspect ratio is about 0.43
Grayscales = {
    10: '@%#*+=-:. ', # TODO change these
    70: "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\\|()1{}[]?-_+~<>i!lI;:,\"^`'. " # TODO change these
}

# Map taken from https://rabbit.eng.miami.edu/info/htmlchars.html
SVGMaps = {
    '&' : '&amp;',
    '<' : '&lt;',
    '>' : '&gt;',
}


# HACK very dumb and slow way to find all divisors, fix it
# also generator function with yield is better since we care more about
# memory (in the case of huge images) rather than speed
def _divisorGenerator(n: int):
    for i in range(1, int(n/2+1)):
        if n%i == 0: yield i
    yield n

def _getDivisors(n: int):
    return list(_divisorGenerator(n))

def _getUniqueName() -> str:

    part1 = ['Cheap', 'Expensive', 'Nice', 'Ugly', 'Stupid', 'Smart', 'Brilliant', 'Great', 'Pretty', 'Rich']
    part2 = ['Small', 'Tiny', 'Huge', 'Big', 'Miniscule', 'Tall', 'Little', 'Large', 'Colossal', 'Puny']
    part3 = ['Old', 'New', 'Ancient', 'Teen', 'Young', 'Antique', 'Elderly', 'Aged', 'Mature', 'Childish']
    part4 = ['Round', 'Square', 'Angled', 'Convex', 'Oblique', 'Straight', 'Thick', 'Curved', 'Wide', 'Wavy']
    part5 = ['Red', 'Green', 'Cyan', 'Glossy', 'Vibrant', 'Black', 'Grey', 'White', 'Purple', 'Blue']
    part6 = ['Greek', 'French', 'Spanish', 'Italian', 'English', 'Swedish', 'German', 'Japanese', 'Korean', 'Indian']
    part7 = ['Wooden', 'Steel', 'Natural', 'Synthetic', 'Plastic', 'Gold', 'Ceramic', 'Marble', 'Smooth', 'Soft']
    objects = ['Table', 'House', 'Raindrop', 'Car', 'JetEngine', 'Bottle', 'Phone', 'Electron', 'Tree', 'Cat', 'Parrot', 'Candle', 'Coin', 'Bed', 'Printer', 'Tree', 'Leaf', 'Sponge']

    parts = [part1, part2, part3, part4, part5, part6, part7]
    adj1, adj2 = np.random.randint(0, 6, 2)
    pos1, pos2 = np.random.randint(0, 9, 2)
    obj = np.random.randint(0, 17)

    return parts[adj1][pos1] + '_' + parts[adj2][pos2] + '_' + objects[obj]

def _colorsToHex(r: int = 0, g: int = 0, b: int = 0) -> str:
    if not (0 <= r <= 255):
        raise Errors.VariableInvalidValueError('r', r, "RGB values must be between 0 and 255 (inclusive)!")
    if not (0 <= g <= 255):
        raise Errors.VariableInvalidValueError('g', g, "RGB values must be between 0 and 255 (inclusive)!")
    if not (0 <= b <= 255):
        raise Errors.VariableInvalidValueError('b', b, "RGB values must be between 0 and 255 (inclusive)!")
    
    return str.lower(f"#{r:02X}{g:02X}{b:02X}")

def _formatForSVG(char: str):
    if char in SVGMaps:
        char = SVGMaps.get(char)
    return char
