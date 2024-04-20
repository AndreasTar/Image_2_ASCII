# [ ] add convertion from link
# [ ] add colored conversion to colored ascii

# TODO learn how argparse and improve this
# TODO think about making em into classes?
# TODO since characters dont have a square aspect ratio
#   figure out some math or something to fix it?

# Project inspired by this tutorial:
# https://www.geeksforgeeks.org/converting-image-ascii-image-python/

import argparse, pathlib
import numpy as np
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
    for i in range(1, int(n/2+1)):
        if n%i == 0: yield i
    yield n

def getDivisors(n: int):
    return list(divisorGenerator(n))

def calculateAverage(tile: Image):
    npImg = np.array(tile)
    tw, th = npImg.shape

    return np.average(npImg.reshape(tw*th))

def initParser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        usage = 'Usage: converter.py inputFile [-h] [-a] \
            [-wi int] [-wc int] [-he int] [-hc int] \
            [-gsc {10,70}] \
            [-op string] [-on string] \
            [-t {png, jpg, txt}]',
        
        description = 'Program that converts an input image into an ASCII representation.'

    )

def initParserArguments(parser: argparse.ArgumentParser):
    parser.add_argument(
            'inputFile',
            type        =   pathlib.Path,
            help        =   'The path to the file to be converted'
    )
    parser.add_argument(
            '-a', '--auto',
            dest        =   'inputAuto',
            required    =   False,
            action      =   'store_true',
            help        =   'Should the program decide the values on its own? NOT IMPLEMENTED'
    )
    parser.add_argument(
            '-c', '--colored',
            dest        =   'inputColored',
            required    =   False,
            action      =   'store_true',
            help        =   'Should the output image be colored instead of greyscale? NOT IMPLEMENTED'
    )
    parser.add_argument(
            '-wi', '--width',
            dest        =   'inputWidth',
            required    =   False,
            type        =   int,
            help        =   'Tile width in pixels.'
    )
    parser.add_argument(
            '-wc', '--widthcount',
            dest        =   'inputWidthcount',
            required    =   False,
            type        =   int,
            help        = 'How many tiles to create on the X axis. NOT IMPLEMENTED'
    )
    parser.add_argument(
            '-he', '--height',
            dest        =   'inputHeight',
            required    =   False,
            type        =   int,
            help        = 'Tile height in pixels.'
    )
    parser.add_argument(
            '-hc', '--heightcount',
            dest        =   'inputHeightcount',
            required    =   False,
            type        =   int,
            help        = 'How many tiles to create on the Y axis. NOT IMPLEMENTED'
    )
    parser.add_argument(
            '-gsc', '--grayscalecount',
            dest        =   'inputGrayScaleCount',
            required    =   False,
            type        =   int,
            choices     =   [10,70],
            default     =   70,
            help        =   'How many characters to use for the ASCII representation.'
    )
    parser.add_argument(
            '-op', '--outputfilepath',
            dest        =   'inputFileOut',
            required    =   False,
            type        =   pathlib.Path,
            default     =   'out.txt',
            help        =   'The full path of the output file. NOT IMPLEMENTED'
    )
    parser.add_argument(
            '-on', '--outputfilename',
            dest        =   'inputFileNameOut',
            required    =   False,
            type        =   str,
            default     =   'out.txt',
            help        =   'The name of the output file. Will be stored in the same folder. NOT IMPLEMENTED'
    )
    parser.add_argument(
            '-t', '--outputfiletype',
            dest        =   'inputFileTypeOut',
            required    =   False,
            choices     =   ['png', 'jpg', 'txt'],
            default     =   'txt',
            help        =   'The format of the output file. NOT IMPLEMENTED'
    )
      
def configureArgs(args: argparse.Namespace):

    grayscaleImage = Image.open(args.inputFile).convert('L')

    imageWidth, imageHeight = grayscaleImage.size
    print(f"\tInput image dimensions: {imageWidth} x {imageHeight} pixels")

    inputWidth = args.inputWidth
    if (not inputWidth):
        divs = getDivisors(imageWidth)
        print("Input the desired width scale from the list:")
        print(divs)
        while True:
            inputWidth = int(input())
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
            inputHeight = int(input())
            if not divs.__contains__(inputHeight):
                print("Input a valid option from the list!")
            else: break
    print(f"Using tile height size: {inputHeight}")

    inputGSCount = args.inputGrayScaleCount
    print(f"Using grayscale ascii detail: {inputGSCount}")

    outFile = args.inputFileOut
    #outFile = outFile.absolute().as_uri() + '.txt'

    return grayscaleImage, \
        imageWidth, imageHeight, \
        inputWidth, inputHeight, \
        inputGSCount, outFile

def convert2Ascii(image: Image, imageHeight, tileHeight, imageWidth, tileWidth):

    global gscale1, gscale2

    asciiImage = []

    rowNum = int(imageHeight / tileHeight)
    colNum = int(imageWidth / tileWidth)

    for r in range(rowNum):
        ytop = r * tileHeight
        ybot = (r+1) * tileHeight
        if r == rowNum-1:
            ybot = imageHeight
        asciiImage.append('')

        for c in range(colNum):
            xleft = c * tileWidth
            xright = (c+1) * tileWidth
            if c == colNum-1:
                xright = imageWidth
            
            tile = image.crop((xleft, ytop, xright, ybot))

            avg = int(calculateAverage(tile))

            val = gscale1[int((avg*69)/255)]
            asciiImage[r] += val

    return asciiImage


def main():
    argParser = initParser()

    initParserArguments(argParser)

    args = argParser.parse_args()

    gsimg, imgwidth, imgheight, inwidth, inheight, gsc, outfile = configureArgs(args)

    asciiImg = convert2Ascii(gsimg, imgheight, inheight, imgwidth, inwidth)

    f = open(outfile, 'w')
    for r in asciiImg:
        f.write(r + '\n')
    f.close()
    print("DONEEEEEE\n")
	

if __name__ == '__main__':
	main()