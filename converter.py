# [ ] add convertion from link
# [ ] add colored conversion to colored ascii

# TODO learn how argparse and improve this
# TODO think about making em into classes?

# Project inspired by this tutorial:
# https://www.geeksforgeeks.org/converting-image-ascii-image-python/

import argparse, pathlib
from PIL import Image

# gray scale level values from: 
# http://paulbourke.net/dataformats/asciiart/

# 70 levels of gray
gscale1 = "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\|()1{}[]?-_+~<>i!lI;:,\"^`'. "

# 10 levels of gray
gscale2 = '@%#*+=-:. '

# HACK very dumb and slow way to find all divisors, fix it
# also generator function with yield is better since we care more about
# memory (in the case of huge images) rather than speed
def divisorGenerator(n: int):
    for i in range(1, n/2+1):
        if n%i == 0: yield i
    yield n

def getDivisors(n: int):
    return list(divisorGenerator(n))

def initParser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser()

def initParserArguments(parser: argparse.ArgumentParser):
    parser.add_argument(
            'file',
            dest        =   'inputFile',
            required    =   True,
            type        =   pathlib.Path
    )
    parser.add_argument(
            '-w', '--width',
            dest        =   'inputWidth',
            required    =   False,
            type        =   int,
    )
    parser.add_argument(
            '-h', '--height',
            dest        =   'inputHeight',
            required    =   False,
            type        =   int,
    )
    parser.add_argument(
            '-gsc', '--grayscalecount',
            dest        =   'inputGrayScaleCount',
            required    =   False,
            type        =   int,
            choices     =   range(2,71),
            default     =   70,
    )
    parser.add_argument(
            '-o', '--outputfilepath',
            dest        =   'inputFileOut',
            required    =   False,
            type        =   pathlib.Path,
            default     =   'out',
    )
    parser.add_argument(
            '-t', '--outputfiletype',
            dest        =   'inputFileOut',
            required    =   False,
            choices     =   ['png', 'jpg', 'txt'],
            default     =   'txt',
    )
      
def configureArgs(args: argparse.Namespace):
    pass

def convert2Ascii(args: argparse.Namespace):

    global gscale1, gscale2

    grayscaleImage = Image.open(args.inputFile).convert('L')

    imageWidth, imageHeight = grayscaleImage.size
    print(f"\tInput image dimensions: {imageWidth} x {imageHeight} pixels")

    inputWidth = args.inputWidth
    if (not inputWidth):
        divs = getDivisors(imageWidth)
        print("Input the desired width scale from the list:")
        print(divs)
        while True:
            inputWidth = input()
            if not divs.__contains__(inputWidth):
                print("Input a valid option from the list!")
            else: break
    print(f"Using tile width size: {inputWidth}")

    inputHeight = args.inputHeight
    if (not inputHeight):
        divs = getDivisors(imageHeight)
        print("Input the desired height scale from the list:")
        print(divs)
        while True:
            inputHeight = input()
            if not divs.__contains__(inputHeight):
                print("Input a valid option from the list!")
            else: break
    print(f"Using tile height size: {inputHeight}")

    inputGSCount = args.inputGrayScaleCount
    print(f"Using grayscale ascii detail: {inputGSCount}")




def main():
    argParser = initParser()

    initParserArguments(argParser)

    args = argParser.parse_args()

    configureArgs(args)

    asciiImg = convert2Ascii()
	

if __name__ == '__main__':
	main()