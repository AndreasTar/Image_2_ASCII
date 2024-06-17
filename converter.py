###########################################################################
# Copyright (c) 2024, Andy Pandy                                          #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################

# [ ] add convertion from link
# [ ] add colored conversion to colored ascii

# TODO learn how argparse and improve this
# TODO since characters dont have a square aspect ratio
#   figure out some math or something to fix it?
#   maybe also implement a recommended input (like auto)
# TODO add maybe a direct output? i guess you can do that by just returning the final array

# Project inspired by this tutorial:
# https://www.geeksforgeeks.org/converting-image-ascii-image-python/
# More details at:
# https://en.wikipedia.org/wiki/ASCII_art#:~:text=of%20Unicode.-,Methods%20for%20generating%20ASCII%20art

from src import frontend

def main():
    print("Starting tool...\n")
    frontend.SetupParser()
    frontend.RunTool()
	

if __name__ == '__main__':
	main()