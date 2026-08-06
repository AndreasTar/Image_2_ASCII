###########################################################################
# Copyright (c) 2024-2026, Andy Pandy                                          #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################

"""
The graphical frontend.

One of two ways into the same engine. `src/frontend.py` reads flags and prompts; this
reads widgets. Both end up handing a `src.config.Config` to `src.midend.execute`, and
neither knows the other exists.

Nothing in `src` imports anything from here, which is what lets the command line build
into an executable with no Qt in it at all.
"""
