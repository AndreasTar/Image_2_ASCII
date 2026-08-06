###########################################################################
# Copyright (c) 2024-2026, Andreas Tarasidis (Andy Pandy)                 #
#                                                                         #
# Original repo: https://github.com/AndreasTar/Image_2_ASCII              #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################

"""
Running a conversion without freezing the window.

A thousand frame video is minutes of work. Doing that on the thread that draws the window
would leave the whole application unresponsive and, on Windows, greyed out and reported as
not responding, so every conversion happens here instead.

The engine reports progress by calling whatever it was given. Those calls arrive on this
thread, so each one is turned straight into a signal; Qt queues them across to the window,
which is the only thread allowed to touch a widget.
"""

import pathlib as pl

from PySide6.QtCore import QThread, Signal

from gui import session
from src import midend, tools


class ConversionWorker(QThread):
    """
    One conversion, start to finish.

    Deliberately single use. The source it opens is consumed by the run, so a second run
    means a second worker, which also keeps a superseded preview from writing its result
    over a newer one.
    """

    progressed = Signal(int, int)       # framesDone, framesTotal
    logged = Signal(str)
    # The equivalent command line, emitted before the work starts. Kept separate from
    # `logged` so the window can show it for every conversion including previews, without
    # also taking the engine's running commentary on each one.
    commanded = Signal(str)
    # Not called `finished`. QThread already has a signal by that name, which Qt emits when
    # the thread itself ends and which the window relies on to clean the worker up.
    succeeded = Signal(object, object)  # result, config
    failed = Signal(str)

    def __init__(self, settings: dict, inputPath: pl.Path, outputPath: pl.Path, *,
                 shouldSave: bool, preview: bool, parent = None) -> None:
        super().__init__(parent)

        self.pSettings = settings
        self.pInputPath = inputPath
        self.pOutputPath = outputPath
        self.pShouldSave = shouldSave
        self.pPreview = preview
        self.pCancelled = False

    def cancel(self) -> None:
        """
        Asks the run to stop reporting.

        The engine has no way to be interrupted part way through, so this does not stop the
        work. What it does is make sure a preview the user has already moved on from cannot
        come back and overwrite the pane with a stale picture.
        """
        self.pCancelled = True

    def run(self) -> None:
        if not self.pCancelled:
            lines = [session.commandLine(self.pSettings, self.pInputPath, self.pOutputPath,
                                         preview = self.pPreview)]
            lines += session.commandNotes(self.pSettings, self.pPreview)
            self.commanded.emit('\n'.join(lines))

        try:
            config = session.buildConfig(
                self.pSettings,
                self.pInputPath,
                self.pOutputPath,
                shouldSave  =   self.pShouldSave,
                preview     =   self.pPreview,
                progress    =   self.pProgress,
                log         =   self.pLog,
            )

            result = midend.execute(config)
        except tools.Errors.GenericError as e:
            if not self.pCancelled:
                self.failed.emit(e.errorMsg)
            return
        except Exception as e:
            # Anything the engine did not expect still has to reach the user as a message
            # rather than as a silently dead thread.
            if not self.pCancelled:
                self.failed.emit(f"{type(e).__name__}: {e}")
            return

        if not self.pCancelled:
            self.succeeded.emit(result, config)

    # ---- called from this thread by the engine ----

    def pProgress(self, done: int, total: int) -> None:
        if not self.pCancelled:
            self.progressed.emit(done, total)

    def pLog(self, message: str) -> None:
        if not self.pCancelled:
            self.logged.emit(message.strip('\n'))
