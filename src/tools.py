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

# NOTE consider having the params be a global struct or something using this:
# https://stackoverflow.com/questions/35988/c-like-structures-in-python

class Errors:
    class GenericError(Exception):

        errorMsg = "Generic error message!"

        def __init__(self, error_msg = errorMsg, *args: object) -> None:
            self.errorMsg = error_msg

            super().__init__(self.errorMsg)
    
    class Unimplemented(GenericError):

        def __init__(self, *args: object) -> None:
            super().__init__("FUNCTION IS NOT IMPLEMENTED!")

    class VariableNotInitialisedError(GenericError):

        varName = ""
        errorMsg = f"Value was accessed before being initialised!"

        def __init__(self, var_name: str, error_msg = errorMsg, *args: object) -> None:
            self.varName = var_name
            self.errorMsg = error_msg + f"\n\t\tVariable Name -> {var_name}"

            super().__init__(self.errorMsg)

    class VariableInvalidValueError(GenericError):

        varName = ""
        varValue = None
        errorMsg = "Variable has an invalid value!"

        def __init__(self, var_name: str, var_value, error_msg = errorMsg, *args: object) -> None:
            self.varName = var_name
            self.varValue = var_value
            self.errorMsg = error_msg + f"\n\t\tVariable Name -> {var_name}\n\t\tVariable Value -> {var_value}"

            super().__init__(self.errorMsg)


class ValidTypes(Enum):
    TXT = 0
    JPG = 1
    PNG = 2
    XML = 3
    SVG = 4

    @classmethod
    def asList(cls):
        return [v.name.lower() for v in cls]
    
    @classmethod
    def getImageTypes(cls):
        return [v.name for v in cls if v.value in [1, 2]]


# gray scale level values from: 
# http://paulbourke.net/dataformats/asciiart/
# for Courier font, aspect ratio is about 0.43
GRAYSCALES = {
    10: '@%#*+=-:. ', # TODO change these
    70: "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\\|()1{}[]?-_+~<>i!lI;:,\"^`'. " # TODO change these
}

# Map taken from https://rabbit.eng.miami.edu/info/htmlchars.html
SVG_MAPS = {
    '&' : '&amp;',
    '<' : '&lt;',
    '>' : '&gt;',
}


# HACK very dumb and slow way to find all divisors, fix it
# also generator function with yield is better since we care more about
# memory (in the case of huge images) rather than speed
def pDivisorGenerator(n: int):
    for i in range(1, int(n/2+1)):
        if n%i == 0: yield i
    yield n

def pGetDivisors(n: int):
    return list(pDivisorGenerator(n))

def pGetUniqueName() -> str:

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

def pColorsToHex(r: int = 0, g: int = 0, b: int = 0) -> str:
    if not (0 <= r <= 255):
        raise Errors.VariableInvalidValueError('r', r, "RGB values must be between 0 and 255 (inclusive)!")
    if not (0 <= g <= 255):
        raise Errors.VariableInvalidValueError('g', g, "RGB values must be between 0 and 255 (inclusive)!")
    if not (0 <= b <= 255):
        raise Errors.VariableInvalidValueError('b', b, "RGB values must be between 0 and 255 (inclusive)!")
    
    return str.lower(f"#{r:02X}{g:02X}{b:02X}")

def pFormatForSVG(char: str) -> str:
    # Gets key, or defaults to returning the character
    return SVG_MAPS.get(char, char)
