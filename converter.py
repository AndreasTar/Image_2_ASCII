###########################################################################
# Copyright (c) 2024, Andy Pandy                                          #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################

# Project inspired by this tutorial:
# https://www.geeksforgeeks.org/converting-image-ascii-image-python/
# More details at:
# https://en.wikipedia.org/wiki/ASCII_art#:~:text=of%20Unicode.-,Methods%20for%20generating%20ASCII%20art

from src import frontend
from src.tools import APP_VERSION


def main():
    print(f"\n{"=-=-"*18}")
    print(f"\
\n`Image2Ascii` tool, version: {APP_VERSION}\n\n\
Made by: Andreas Tarasidis\nGithub Link: https://github.com/AndreasTar \n\
Repository Link: https://github.com/AndreasTar/Image_2_ASCII \n\
Licensed under the BSD-style license found in the LICENSE file of the root directory.\n"
    )
    print(f"{"=-=-"*18}\n")
    
    print("Starting tool...")
    frontend.setupParser()
    frontend.runTool()
    print("\nTool finished with no errors!\n")
	

if __name__ == '__main__':
	main()
