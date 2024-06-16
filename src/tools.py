###########################################################################
# Copyright (c) 2024, Andy Pandy                                          #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################

class ValueNotInitialisedError(Exception):

    errorMsg = "Value was accessed before being initialised: "

    def __init__(self, value_name: str, message = errorMsg, *args: object) -> None:
        super().__init__(message + value_name)





# HACK very dumb and slow way to find all divisors, fix it
# also generator function with yield is better since we care more about
# memory (in the case of huge images) rather than speed
def _divisorGenerator(n: int):
    for i in range(1, int(n/2+1)):
        if n%i == 0: yield i
    yield n

def _getDivisors(n: int):
    return list(_divisorGenerator(n))