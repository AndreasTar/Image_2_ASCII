###########################################################################
# Copyright (c) 2024, Andy Pandy                                          #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################

import numpy as np

class ValueNotInitialisedError(Exception):

    errorMsg = "Value was accessed before being initialised: "
    value_name = ''

    def __init__(self, value_name: str, message = errorMsg, *args: object) -> None:
        super().__init__(message + value_name)
        self.value_name = value_name


class ValueInvalidError(Exception):
    errorMsg = "Value was invalid: "
    value_name = ''
    value = None

    def __init__(self, value_name: str, value, message = errorMsg, *args: object) -> None:
        super().__init__(message + value_name + f" -> {value}")
        self.value_name = value_name
        self.value = value


ValidTypes = ['txt', 'jpg', 'png', 'xml']


# gray scale level values from: 
# http://paulbourke.net/dataformats/asciiart/

Grayscales = {
    10: '@%#*+=-:. ', # TODO change these
    70: "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\|()1{}[]?-_+~<>i!lI;:,\"^`'. " # TODO change these
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

def _colorsToHex(r: int = 0, g: int = 0, b: int = 0):
    if 
    return str.lower(f"#{hex(r)[2:]}{hex(g)[2:]}{hex(b)[2:]}")
