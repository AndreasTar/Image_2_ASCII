# [ ] add convertion from link
# [ ] add colored conversion to colored ascii

# TODO learn how argparse and improve this
# TODO think about making em into classes?
# TODO since characters dont have a square aspect ratio
#   figure out some math or something to fix it?
#   maybe also implement a recommended input (like auto)

# Project inspired by this tutorial:
# https://www.geeksforgeeks.org/converting-image-ascii-image-python/

import argparse, pathlib
import numpy as np
from PIL import Image
from textwrap import dedent
from enum import Enum

# gray scale level values from: 
# http://paulbourke.net/dataformats/asciiart/

# 70 levels of gray
gscale1 = "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\|()1{}[]?-_+~<>i!lI;:,\"^`'. "

# 10 levels of gray
gscale2 = '@%#*+=-:. '

validTypes = ['png', 'jpg', 'xml', 'txt']


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
#         usage = dedent('Usage: converter.py inputFile [-h] [-a] \
# [-wi int] [-wc int] [-he int] [-hc int] \
# [-gsc {10,70}] \
# [-op string] [-on string] \
# [-t {png, jpg, xml, txt}]'
#         ),
        
        description = 'Program that converts an input image into an ASCII representation.'

    )


def initParserArguments(parser: argparse.ArgumentParser):

    global validTypes

    wgroup = parser.add_mutually_exclusive_group()
    hgroup = parser.add_mutually_exclusive_group()

    parser.add_argument(    #input file
            'inputFile',
            type        =   pathlib.Path,
            help        =   'The path to the file to be converted'
    )
    parser.add_argument(    # automatic NI
            '-a', '--auto',
            dest        =   'inputAuto',
            required    =   False,
            action      =   'store_true',
            help        =   'Should the program decide the values on its own? NOT IMPLEMENTED'
    )
    parser.add_argument(    # colored NI
            '-c', '--colored',
            dest        =   'inputColored',
            required    =   False,
            action      =   'store_true',
            help        =   'Should the output image be colored instead of greyscale? NOT IMPLEMENTED'
    )

    wgroup.add_argument(    # width pixel per tile
            '-wi', '--width',
            dest        =   'inputWidth',
            required    =   False,
            type        =   int,
            help        =   'Tile width in pixels.',
            metavar     =   'INTEGER'
    )
    wgroup.add_argument(    # width total tiles
            '-wc', '--widthcount',
            dest        =   'inputWidthcount',
            required    =   False,
            type        =   int,
            help        =   'MAX amount of tiles to create on the X axis.',
            metavar     =   'INTEGER'
    )

    hgroup.add_argument(    # height pixel per tile
            '-hi', '--height',
            dest        =   'inputHeight',
            required    =   False,
            type        =   int,
            help        =   'Tile height in pixels.',
            metavar     =   'INTEGER'
    )
    hgroup.add_argument(    # height total tiles
            '-hc', '--heightcount',
            dest        =   'inputHeightcount',
            required    =   False,
            type        =   int,
            help        =   'MAX amount of tiles to create on the Y axis.',
            metavar     =   'INTEGER'
    )

    parser.add_argument(    # how many grayscale TODO
            '-gsc', '--grayscalecount',
            dest        =   'inputGrayScaleCount',
            required    =   False,
            type        =   int,
            choices     =   [10,70],
            default     =   70,
            help        =   'How many characters to use for the ASCII representation.'
    )

    parser.add_argument(    # output path
            '-op', '--outputfilepath',
            dest        =   'inputFileOut',
            required    =   False,
            type        =   pathlib.Path,
            #default     =   '\\out',
            help        =   'The full path of the output file. NOT IMPLEMENTED',
            metavar     =   'PATH'
    )
    parser.add_argument(    # output type
            '-t', '--outputfiletype',
            dest        =   'inputFileTypeOut',
            required    =   False,
            choices     =   validTypes,
            default     =   'txt',
            help        =   'The format of the output file. NOT IMPLEMENTED'
    )
      
def configureArgs(args: argparse.Namespace):
    global validTypes

    inImg = Image.open(args.inputFile).convert('L')

    imgWidth, imgHeight = inImg.size
    print(f"\nInput image dimensions: {imgWidth} x {imgHeight} pixels")

    manageAuto(args)

    manageColored(args)

    tileWidth = manageWidth(args, imgWidth)

    tileHeight = manageHeight(args, imgHeight)

    tilecountw = int(imgWidth/tileWidth)
    tilecounth = int(imgHeight/tileHeight)
    print(f"Using tile size in pixels (w x h): {tileWidth} x {tileHeight}")
    print(f"Total tile count \n\tper axis (w x h): {tilecountw} x {tilecounth}\n\ttotal: {tilecountw*tilecounth}")

    inGSCount =  manageGrayscale(args)
    print(f"Using grayscale ascii detail: {inGSCount}")

    outFile = manageOutput(args)
    print(f"Output file path: {outFile}")

    return inImg, \
        imgWidth, imgHeight, \
        tileWidth, tileHeight, \
        inGSCount, outFile

def convert2Ascii(image: Image, imageHeight, imageWidth, tileHeight, tileWidth):

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

def manageAuto(args: argparse.Namespace):
    inAuto = args.inputAuto

def manageColored(args: argparse.Namespace):
    inColored = args.inputColored

def manageWidth(args: argparse.Namespace, imgWidth: int) -> int:
    inWidth = args.inputWidth
    inWidthCount = args.inputWidthcount
    tileWidth = 0
    if (not (inWidth or inWidthCount)): # if we get neither
        divs = getDivisors(imgWidth)
        print("Input the desired tile width size per pixel from the list:")
        print(divs)
        while True:
            inWidth = int(input())
            if not divs.__contains__(inWidth):
                print("Input a valid option from the list!") # TODO add auto option and custom option
            else:
                tileWidth = inWidth
                break
    elif (inWidth): # if we get tile pixel size
        if (inWidth < 1 or inWidth > imgWidth):
            print("Invalid tile size! Exiting...")
            exit()
        tileWidth = inWidth
    else:           # if we get tile count
        if (inWidthCount < 1 or inWidthCount > imgWidth):
            print("Invalid tile size! Exiting...")
            exit()
        tileWidth = int(np.ceil(imgWidth / inWidthCount))
    
    return tileWidth

def manageHeight(args: argparse.Namespace, imgHeight: int) -> int:
    inHeight = args.inputHeight
    inHeightCount = args.inputHeightcount
    tileHeight = 0
    if (not (inHeight or inHeightCount)): # if we get neither
        divs = getDivisors(imgHeight)
        print("Input the desired tile height size per pixel from the list:")
        print(divs)
        while True:
            inHeight = int(input())
            if not divs.__contains__(inHeight):
                print("Input a valid option from the list!") # TODO add auto option and custom option
            else: 
                tileHeight = inHeight
                break
    elif (inHeight): # if we get tile pixel size
        if (inHeight < 1 or inHeight > imgHeight):
            print("Invalid tile size! Exiting...")
            exit()
        tileHeight = inHeight
    else:           # if we get tile count
        if (inHeightCount < 1 or inHeightCount > imgHeight):
            print("Invalid tile size! Exiting...")
            exit()
        tileHeight = int(np.ceil(imgHeight / inHeightCount))
    
    return tileHeight

def manageGrayscale(args: argparse.Namespace):
    inGSCount = args.inputGrayScaleCount
    return inGSCount

def manageOutput(args: argparse.Namespace) -> pathlib.Path:

    outFilePath:pathlib.Path = args.inputFileOut
    outFileType = args.inputFileTypeOut
    
    # get input path
    #   if it exists, create the file there with the name given, whatever that is, and append type at the end
    #   if not, assume current folder and use unique recognisable name and append type at the end

    outFile = ""

    if (not outFilePath):
        outFile = getUniqueName()
        #outFile = "temporary_name"
        outFile += outFileType
    else:
        outFile = outFilePath + outFileType

    outFile = pathlib.Path.joinpath("", outFile)
    return outFile

def getUniqueName() -> str:

    part1 = ['Cheap', 'Expensive', 'Nice', 'Ugly', 'Stupid', 'Smart', 'Brilliant', 'Great', 'Pretty', 'Rich']
    part2 = ['Small', 'Tiny', 'Huge', 'Big', 'Miniscule', 'Tall', 'Little', 'Large', 'Colossal', 'Puny']
    part3 = ['Old', 'New', 'Ancient', 'Teen', 'Young', 'Antique', 'Elderly', 'Aged', 'Mature', 'Childish']
    part4 = ['Round', 'Square', 'Angled', 'Convex', 'Oblique', 'Straight', 'Thick', 'Curved', 'Wide', 'Wavy']
    part5 = ['Red', 'Green', 'Cyan', 'Glossy', 'Vibrant', 'Black', 'Grey', 'White', 'Purple', 'Blue']
    part6 = ['Greek', 'French', 'Spanish', 'Italian', 'English', 'Swedish', 'German', 'Japanese', 'Korean', 'Indian']
    part7 = ['Wooden', 'Steel', 'Natural', 'Synthetic', 'Plastic', 'Gold', 'Ceramic', 'Marble', 'Smooth', 'Soft']

    parts = [part1, part2, part3, part4, part5, part6, part7]
    adj1, adj2, adj3, pos1, pos2, pos3 = np.random.random_integers(0, 6, 6)

    return parts[adj1][pos1] + '_' + parts[adj2][pos2] + '_' + parts[adj3][pos3]
    



def main():
    argParser = initParser()

    initParserArguments(argParser)

    args = argParser.parse_args()

    gsimg, imgwidth, imgheight, inwidth, inheight, gsc, outfile = configureArgs(args)

    asciiImg = convert2Ascii(gsimg, imgheight, imgwidth, inheight, inwidth)

    f = open(outfile, 'w')
    for r in asciiImg:
        f.write(r + '\n')
    f.close()
    print("DONEEEEEE\n")
	

if __name__ == '__main__':
	main()