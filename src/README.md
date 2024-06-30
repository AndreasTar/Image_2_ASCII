###########################################################################
# Copyright (c) 2024, Andy Pandy                                          #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################

This readme will just explain the general layout of the source code, and the responsibilites of each file,
and also will contain the TODO list for internal operations.

### main.py
Tells **frontend.rs** to make parser and then run\
Also gets result, error or ascii, and shows it on screen or returns it

### frontend
Holds parser, and prolly not use it much after initialisation\
Makes parser, handles return and error\
Surface checks if flags are ok, and either asks user for input or errors\
Calls stuff from midend depending on flags

### midend
Holds the ascii and color arrays\
Communicates with backend to tell it what to process\
Depending on the function called, it provides backend with the data to process\
Also calls the converters to make the jpg png etc\
It handles the saving of the file to the location needed (may need to extract this)

### backend
Holds all the math and processing that the tool needs\
Where the 'actual' work happens, seperated in functions\

### tools
Has all custom global data and exceptions, as well as some helpful functions

### converters
Houses the code for converting to all output formats

# -=-=-=-=-=-=-=-=-TODOs-=-=-=-=-=-=-=-=-

- [ ] add convertion from link

- TODO learn how argparse and improve this
- TODO since characters dont have a square aspect ratio
  - figure out some math or something to fix it?
  - maybe also implement a recommended input (like auto)
- TODO add maybe a direct output? i guess you can do that by just returning the final array
- TODO also maybe use input file name optionally when saving
- NOTE also pil has functions for opening and saving files, so check them out, maybe pathlib aint needed
- TODO also have flag to consider alpha?
- TODO i think some cmds can output colored text, but either way add option to output on screen?