###########################################################################
# Copyright (c) 2024, Andy Pandy                                          #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################

"""
The window.

Settings on the left, source and result side by side on the right, progress and log along
the bottom. Changing any setting re-previews on its own after a short pause, so the effect
of a threshold or a character set is something you watch rather than something you run.

Saving is always a separate, deliberate act. Nothing here writes to disk until the user
picks a destination, which is what makes it safe to preview continuously.
"""

import pathlib as pl

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QPlainTextEdit, QProgressBar, QPushButton, QSplitter, QVBoxLayout, QWidget,
)

from gui import session, theme
from gui.controls import SettingsPanel
from gui.preview import PreviewPane
from gui.worker import ConversionWorker
from src import tools

# How long the controls have to stay still before a preview starts. Long enough that
# dragging a slider does not queue a conversion per pixel, short enough to feel immediate.
PREVIEW_DELAY_MS = 260

READABLE_INPUTS = (
    "Images and animations (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tif *.tiff *.mp4 *.mov *.avi *.mkv *.webm);;"
    "All files (*)"
)


class MainWindow(QMainWindow):

    def __init__(self) -> None:
        super().__init__()

        self.pInputPath: pl.Path | None = None
        self.pPreviewWorker: ConversionWorker | None = None
        self.pSaveWorker: ConversionWorker | None = None
        self.pLastConfig = None

        self.setWindowTitle(f"Image2Ascii {tools.APP_VERSION}")
        self.resize(1360, 880)
        self.setMinimumSize(940, 620)

        self.pBuildUi()
        self.pWireSignals()
        self.pSetBusy(False)
        self.pUpdateActions()

    # ================= Construction ================

    def pBuildUi(self) -> None:
        self.pSettings = SettingsPanel()
        # Wide enough for the longest caption plus its control. Below this the cards clip
        # rather than scroll, because the panel scrolls vertically only.
        self.pSettings.setMinimumWidth(380)
        self.pSettings.setMaximumWidth(520)

        self.pPreview = PreviewPane()

        right = QWidget()
        rightLayout = QVBoxLayout(right)
        rightLayout.setContentsMargins(0, 0, 0, 0)
        rightLayout.setSpacing(10)
        rightLayout.addWidget(self.pBuildToolbar())
        rightLayout.addWidget(self.pPreview, 1)
        rightLayout.addWidget(self.pBuildFooter())

        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self.pSettings)
        split.addWidget(right)
        split.setStretchFactor(1, 1)
        split.setChildrenCollapsible(False)
        split.setHandleWidth(10)
        split.setSizes([400, 960])

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(split)

        self.setCentralWidget(container)
        self.statusBar().showMessage("Open an image, a GIF or a video to begin.")

    def pBuildToolbar(self) -> QWidget:
        self.pOpenButton = QPushButton("Open…")
        self.pOpenButton.setToolTip("Choose an image, animation or video to convert.")

        self.pFileLabel = QLabel("No file open")
        self.pFileLabel.setObjectName('Hint')

        self.pAsPicture = QCheckBox("Text as picture")
        self.pAsPicture.setChecked(True)
        self.pAsPicture.setToolTip(
            "Draw TXT, XML and SVG results as an image so they line up with the source. "
            "Off shows the characters themselves. Either way, the saved file is the same."
        )

        self.pZoomOut = QPushButton("−")
        self.pZoomIn = QPushButton("+")
        self.pFit = QPushButton("Fit")
        for button in (self.pZoomOut, self.pZoomIn):
            button.setFixedWidth(34)

        self.pSaveButton = QPushButton("Convert && Save…")
        self.pSaveButton.setObjectName('Primary')
        self.pSaveButton.setToolTip("Run the conversion at full length and write it to a file.")

        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.pOpenButton)
        layout.addWidget(self.pFileLabel, 1)
        layout.addWidget(self.pAsPicture)
        layout.addWidget(self.pZoomOut)
        layout.addWidget(self.pZoomIn)
        layout.addWidget(self.pFit)
        layout.addWidget(self.pSaveButton)

        return bar

    def pBuildFooter(self) -> QWidget:
        self.pProgress = QProgressBar()
        self.pProgress.setTextVisible(False)
        self.pProgress.setFixedHeight(6)

        self.pLog = QPlainTextEdit()
        self.pLog.setObjectName('Log')
        self.pLog.setReadOnly(True)
        self.pLog.setFixedHeight(96)
        self.pLog.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        frame = QFrame()
        frame.setObjectName('Pane')
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)
        layout.addWidget(self.pProgress)
        layout.addWidget(self.pLog)

        return frame

    def pWireSignals(self) -> None:
        self.pOpenButton.clicked.connect(self.openFile)
        self.pSaveButton.clicked.connect(self.convertAndSave)
        self.pFit.clicked.connect(self.pPreview.fitToWindow)
        self.pZoomIn.clicked.connect(lambda: self.pPreview.zoomBy(1.25))
        self.pZoomOut.clicked.connect(lambda: self.pPreview.zoomBy(1 / 1.25))
        self.pAsPicture.toggled.connect(self.pSchedulePreview)

        self.pDebounce = QTimer(self)
        self.pDebounce.setSingleShot(True)
        self.pDebounce.setInterval(PREVIEW_DELAY_MS)
        self.pDebounce.timeout.connect(self.pStartPreview)

        self.pSettings.changed.connect(self.pSchedulePreview)

    # ================= Opening ================

    def openFile(self) -> None:
        chosen, _ = QFileDialog.getOpenFileName(self, "Open an image", "", READABLE_INPUTS)
        if not chosen:
            return

        self.loadFile(pl.Path(chosen))

    def loadFile(self, path: pl.Path) -> None:
        try:
            image, isAnimated, frameCount, size = session.firstFrame(path)
        except tools.Errors.GenericError as e:
            self.pShowError("That file could not be opened", e.errorMsg)
            return
        except Exception as e:
            self.pShowError("That file could not be opened", f"{type(e).__name__}: {e}")
            return

        self.pInputPath = path
        self.pFileLabel.setText(f"{path.name}   —   {size[0]} x {size[1]}"
                                + (f", {frameCount} frames" if isAnimated else ""))

        self.pPreview.setSource(image, f"SOURCE  ·  {path.name}")
        self.pPreview.clearResult("Converting…")
        self.pSettings.setSourceInfo(size, isAnimated, frameCount)

        self.pLog.clear()
        self.pNote(f"Opened {path.name} ({size[0]} x {size[1]}"
                   + (f", {frameCount} frames)" if isAnimated else ")"))

        self.pUpdateActions()
        self.pStartPreview()

    # ================= Previewing ================

    def pSchedulePreview(self) -> None:
        if self.pInputPath is not None:
            self.pDebounce.start()

    def pStartPreview(self) -> None:
        if self.pInputPath is None or self.pSaveWorker is not None:
            return

        if self.pPreviewWorker is not None:
            self.pPreviewWorker.cancel()

        worker = ConversionWorker(
            self.pSettings.settings(),
            self.pInputPath,
            # Never written, but a Config needs somewhere to point. Beside the input rather
            # than in the working directory, so that nothing could land somewhere surprising
            # even if the no-saving guarantee were ever broken.
            self.pInputPath.with_name(f"{self.pInputPath.stem}_preview"),
            shouldSave  =   False,
            preview     =   True,
            parent      =   self,
        )
        worker.commanded.connect(self.pShowCommand)
        worker.succeeded.connect(self.pPreviewReady)
        worker.failed.connect(self.pPreviewFailed)
        worker.finished.connect(lambda w = worker: self.pRetire(w))

        self.pPreviewWorker = worker
        self.statusBar().showMessage("Previewing…")
        worker.start()

    def pPreviewReady(self, result, config) -> None:
        self.pLastConfig = config
        self.pShowResult(result, config)
        self.statusBar().showMessage(
            f"Preview: {config.widthCount} x {config.heightCount} tiles, "
            f"{config.outputType.name}, {config.backend.deviceName}"
        )

    def pPreviewFailed(self, message: str) -> None:
        self.pPreview.clearResult(message)
        self.statusBar().showMessage("Preview failed.")

    def pShowResult(self, result, config) -> None:
        try:
            kind, payload = session.renderForDisplay(result, config, self.pAsPicture.isChecked())
        except Exception as e:
            self.pPreview.clearResult(f"{type(e).__name__}: {e}")
            return

        label = f"RESULT  ·  {config.outputType.name}"
        if kind == 'image':
            self.pPreview.setResultImage(payload, label)
        else:
            self.pPreview.setResultText(payload, label)

    # ================= Saving ================

    def convertAndSave(self) -> None:
        if self.pInputPath is None:
            return

        settings = self.pSettings.settings()
        suffix = settings['outputType']

        suggested = self.pInputPath.with_name(f"{self.pInputPath.stem}_ascii.{suffix}")
        chosen, _ = QFileDialog.getSaveFileName(
            self, "Save the conversion", str(suggested), f"{suffix.upper()} (*.{suffix});;All files (*)"
        )
        if not chosen:
            return

        target = pl.Path(chosen)
        if target.suffix.lower() != f".{suffix}":
            target = target.with_name(target.name + f".{suffix}")

        if self.pPreviewWorker is not None:
            self.pPreviewWorker.cancel()

        worker = ConversionWorker(
            settings, self.pInputPath, target,
            shouldSave  =   True,
            preview     =   False,
            parent      =   self,
        )
        worker.commanded.connect(self.pShowCommand)
        worker.progressed.connect(self.pProgressed)
        worker.logged.connect(self.pNote)
        worker.succeeded.connect(self.pSaveDone)
        worker.failed.connect(self.pSaveFailed)
        worker.finished.connect(lambda w = worker: self.pRetire(w))

        self.pSaveWorker = worker
        self.pSetBusy(True)
        self.pNote(f"\nConverting to {target}")
        worker.start()

    def pSaveDone(self, result, config) -> None:
        self.pSaveWorker = None
        self.pSetBusy(False)
        self.pShowResult(result, config)
        self.statusBar().showMessage(f"Saved to {config.outputPath}")

    def pSaveFailed(self, message: str) -> None:
        self.pSaveWorker = None
        self.pSetBusy(False)
        self.statusBar().showMessage("Conversion failed.")
        self.pShowError("That combination cannot be saved", message)

    def pProgressed(self, done: int, total: int) -> None:
        self.pProgress.setRange(0, total)
        self.pProgress.setValue(done)

    # ================= Odds and ends ================

    def pRetire(self, worker: ConversionWorker) -> None:
        """
        Lets go of a worker that has run to the end.

        Dropping the reference has to happen together with deleting the object. Deleting it
        alone leaves a Python name pointing at a C++ object that no longer exists, and the
        next thing to touch it — closing the window, which asks every worker whether it is
        still running — fails with an internal object already deleted.
        """
        if self.pPreviewWorker is worker:
            self.pPreviewWorker = None
        if self.pSaveWorker is worker:
            self.pSaveWorker = None

        worker.deleteLater()

    def pSetBusy(self, busy: bool) -> None:
        self.pSaveButton.setEnabled(not busy and self.pInputPath is not None)
        self.pOpenButton.setEnabled(not busy)
        self.pSettings.setEnabled(not busy)

        if busy:
            # Indeterminate until the first frame is counted, which is the right look while
            # a video is still being opened and probed.
            self.pProgress.setRange(0, 0)
        else:
            # Emptied rather than filled. A bar left sitting at 100% reads as a conversion
            # that just finished, whatever the window has actually been doing since.
            self.pProgress.setRange(0, 1)
            self.pProgress.setValue(0)

    def pUpdateActions(self) -> None:
        self.pSaveButton.setEnabled(self.pInputPath is not None)

    def pShowCommand(self, command: str) -> None:
        """
        Writes the command line for the conversion about to run.

        Marked with a prompt so it reads as something to copy rather than as more of the
        engine's chatter, and so the window is never a black box about what it is doing.
        """
        first, *rest = command.splitlines()

        self.pLog.appendPlainText(f"$ {first}")
        for line in rest:
            self.pLog.appendPlainText(line)

    def pNote(self, message: str) -> None:
        for line in message.splitlines():
            self.pLog.appendPlainText(line)

    def pShowError(self, title: str, detail: str) -> None:
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("Image2Ascii")
        box.setText(title)
        box.setInformativeText(detail)
        box.exec()

    def closeEvent(self, event) -> None:
        """
        A conversion cannot be interrupted, so leaving one running past the window it
        reports to would mean signals arriving at a deleted widget. Both workers are told
        to stop reporting and then waited for.
        """
        for worker in (self.pPreviewWorker, self.pSaveWorker):
            if worker is not None and worker.isRunning():
                worker.cancel()
                worker.wait(5000)

        super().closeEvent(event)


def run(argv: list[str]) -> int:
    """Starts the application, optionally with a file already open."""
    from PySide6.QtWidgets import QApplication

    app = QApplication(argv)
    app.setApplicationName("Image2Ascii")
    app.setApplicationVersion(tools.APP_VERSION)
    theme.apply(app)

    window = MainWindow()
    window.show()

    # A path on the command line, which is what a file dropped onto the executable or
    # opened with it becomes.
    if len(argv) > 1:
        candidate = pl.Path(argv[1])
        if candidate.exists():
            window.loadFile(candidate)

    return app.exec()
