###########################################################################
# Copyright (c) 2024, Andy Pandy                                          #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################

"""
Every flag the tool has, as something to click.

The lists of character sets, ramp sizes, output formats and compute backends are read out
of the engine rather than written down again here. Adding a character set to `tools` puts
it in the dropdown with its own description as the tooltip, with nothing to remember to
update in the GUI, which is the only way two frontends stay in step over time.

The panel produces a plain dictionary. Turning that into a `Config` happens in `session`,
so that nothing which knows about widgets also knows about the conversion.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QDoubleSpinBox, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QRadioButton, QScrollArea, QSizePolicy, QSlider, QSpinBox,
    QVBoxLayout, QWidget,
)

from src import compute, tools

# What the character controls can be set to. Mirrors the one-of-these-four argparse group.
CHAR_MODES = ('rampSize', 'customRamp', 'charset', 'pixelart')


def pPair(chooser: QWidget, value: QWidget) -> QWidget:
    """
    --- Private method! ---\n
    A 'what to measure in' dropdown and its number, side by side.

    Each axis is a unit and a quantity, and splitting them across two rows made the panel
    read as four unrelated settings rather than two.
    """
    value.setFixedWidth(84)
    value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    holder = QWidget()
    layout = QHBoxLayout(holder)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    layout.addWidget(chooser, 1)
    layout.addWidget(value)

    return holder


class Section(QFrame):
    """One titled card of related settings."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName('Card')

        self.pOuter = QVBoxLayout(self)
        self.pOuter.setContentsMargins(14, 12, 14, 14)
        self.pOuter.setSpacing(9)

        heading = QLabel(title)
        heading.setObjectName('SectionTitle')
        self.pOuter.addWidget(heading)

        self.pGrid = QGridLayout()
        self.pGrid.setContentsMargins(0, 0, 0, 0)
        self.pGrid.setHorizontalSpacing(10)
        self.pGrid.setVerticalSpacing(8)
        self.pGrid.setColumnStretch(1, 1)
        self.pOuter.addLayout(self.pGrid)

        self.pRow = 0

    def addRow(self, label: str | None, widget: QWidget) -> QWidget:
        if label is None:
            self.pGrid.addWidget(widget, self.pRow, 0, 1, 2)
        else:
            caption = QLabel(label)
            caption.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
            self.pGrid.addWidget(caption, self.pRow, 0)
            self.pGrid.addWidget(widget, self.pRow, 1)

        self.pRow += 1

        return widget

    def addHint(self, text: str) -> QLabel:
        hint = QLabel(text)
        hint.setObjectName('Hint')
        hint.setWordWrap(True)

        return self.addRow(None, hint)


class SliderSpin(QWidget):
    """
    A slider with the number next to it.

    A slider alone cannot be set exactly and a box alone gives no feel for the range, and
    both of those matter for the two settings that use this: a brightness cutoff and an
    edge percentile are things people want to sweep and then pin down.
    """

    valueChanged = Signal(int)

    def __init__(self, low: int, high: int, value: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.pSlider = QSlider(Qt.Orientation.Horizontal)
        self.pSlider.setRange(low, high)
        self.pSlider.setValue(value)

        self.pBox = QSpinBox()
        self.pBox.setRange(low, high)
        self.pBox.setValue(value)
        self.pBox.setFixedWidth(64)
        self.pBox.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(9)
        layout.addWidget(self.pSlider, 1)
        layout.addWidget(self.pBox)

        self.pSlider.valueChanged.connect(self.pFromSlider)
        self.pBox.valueChanged.connect(self.pFromBox)

    def value(self) -> int:
        return self.pBox.value()

    def setValue(self, value: int) -> None:
        self.pBox.setValue(value)

    def pFromSlider(self, value: int) -> None:
        if self.pBox.value() != value:
            self.pBox.setValue(value)

    def pFromBox(self, value: int) -> None:
        if self.pSlider.value() != value:
            self.pSlider.setValue(value)
        self.valueChanged.emit(value)


class SettingsPanel(QScrollArea):
    """
    The whole left hand column.

    `changed` fires for anything that alters the result, so the window can re-preview.
    Output destination and format changes fire it too, because the format decides whether
    the result is a picture or text and therefore which pane it belongs in.
    """

    changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.pImageSize = (0, 0)
        self.pIsAnimated = False
        self.pUpdating = False

        body = QWidget()
        self.pLayout = QVBoxLayout(body)
        self.pLayout.setContentsMargins(2, 2, 8, 2)
        self.pLayout.setSpacing(10)

        self.pBuildGrid()
        self.pBuildCharacters()
        self.pBuildAppearance()
        self.pBuildEdges()
        self.pBuildAnimation()
        self.pBuildOutput()
        self.pBuildCompute()
        self.pLayout.addStretch(1)

        self.setWidget(body)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.pWireSignals()
        self.pSyncEnabled()

    # ================= Construction ================

    def pBuildGrid(self) -> None:
        section = Section("Grid")

        self.pWidthMode = QComboBox()
        self.pWidthMode.addItem("Tiles across", 'count')
        self.pWidthMode.addItem("Pixels per tile", 'pixels')

        self.pWidth = QSpinBox()
        self.pWidth.setRange(1, 100_000)
        self.pWidth.setValue(120)

        self.pHeightMode = QComboBox()
        self.pHeightMode.addItem("Tiles down", 'count')
        self.pHeightMode.addItem("Pixels per tile", 'pixels')

        self.pHeight = QSpinBox()
        self.pHeight.setRange(1, 100_000)
        self.pHeight.setValue(60)

        self.pLinkAspect = QCheckBox("Keep the picture's proportions")
        self.pLinkAspect.setChecked(True)
        self.pLinkAspect.setToolTip(
            "Works the missing axis out from the other one and the character shape, the way "
            "--auto does on the command line."
        )

        self.pCharAspect = QDoubleSpinBox()
        self.pCharAspect.setRange(0.05, 10.0)
        self.pCharAspect.setSingleStep(0.05)
        self.pCharAspect.setDecimals(2)
        self.pCharAspect.setValue(tools.DEFAULT_CHAR_ASPECT)
        self.pCharAspect.setToolTip("Width of a character cell divided by its height (-ca).")

        section.addRow("Width", pPair(self.pWidthMode, self.pWidth))
        section.addRow("Height", pPair(self.pHeightMode, self.pHeight))
        section.addRow(None, self.pLinkAspect)
        section.addRow("Character shape", self.pCharAspect)
        self.pGridHint = section.addHint("")

        self.pLayout.addWidget(section)

    def pBuildCharacters(self) -> None:
        section = Section("Characters")

        self.pModeGroup = QButtonGroup(self)
        self.pModeButtons = {}

        for mode, caption in (
            ('rampSize',   "Built-in ramp"),
            ('charset',    "Character set"),
            ('customRamp', "Custom ramp"),
            ('pixelart',   "Pixel art (no characters)"),
        ):
            button = QRadioButton(caption)
            self.pModeButtons[mode] = button
            self.pModeGroup.addButton(button)
            section.addRow(None, button)

            if mode == 'rampSize':
                self.pRampSize = QComboBox()
                for count in sorted(tools.GRAYSCALES):
                    self.pRampSize.addItem(f"{count} characters", count)
                self.pRampSize.setCurrentIndex(self.pRampSize.findData(70))
                section.addRow(None, self.pRampSize)

            elif mode == 'charset':
                self.pCharSet = QComboBox()
                for name, charSet in sorted(tools.CHARSETS.items()):
                    self.pCharSet.addItem(name, name)
                    self.pCharSet.setItemData(
                        self.pCharSet.count() - 1, charSet.description, Qt.ItemDataRole.ToolTipRole
                    )
                section.addRow(None, self.pCharSet)

            elif mode == 'customRamp':
                self.pCustomRamp = QLineEdit()
                self.pCustomRamp.setObjectName('Ramp')
                self.pCustomRamp.setPlaceholderText("@#+-.  (densest first)")
                section.addRow(None, self.pCustomRamp)

        self.pModeButtons['rampSize'].setChecked(True)
        self.pCharsetHint = section.addHint("")

        self.pLayout.addWidget(section)

    def pBuildAppearance(self) -> None:
        section = Section("Appearance")

        self.pColored = QCheckBox("Colour")
        self.pColored.setToolTip("Colour the output instead of leaving it greyscale (-c).")

        self.pInvert = QCheckBox("Invert")
        self.pInvert.setToolTip("Dense characters on the bright areas instead of the dark ones (-i).")

        self.pDither = QCheckBox("Dither")
        self.pDither.setToolTip(
            "Ordered dithering for the dot based sets (braille, quadrants, halfblocks) instead "
            "of one flat cutoff (-d). Worth it at high tile counts, noisy at low ones."
        )

        self.pAlpha = QCheckBox("Flatten transparency onto black")
        self.pAlpha.setToolTip("Otherwise the alpha channel is ignored (--alpha).")

        self.pUseThreshold = QCheckBox("Two-tone threshold")
        self.pUseThreshold.setToolTip("Collapse the image to two tones at a brightness cutoff (-th).")
        self.pThreshold = SliderSpin(0, 255, 128)

        self.pUseBand = QCheckBox("Keep only a brightness range")
        self.pUseBand.setToolTip(
            "Erase everything outside the range and leave what is inside exactly as it would "
            "have been (-tb). Unlike the two-tone threshold, this does not restyle what it keeps."
        )
        self.pBandLow = SliderSpin(0, 255, 60)
        self.pBandHigh = SliderSpin(0, 255, 200)

        section.addRow(None, self.pColored)
        self.pColourHint = section.addHint("")
        section.addRow(None, self.pInvert)
        section.addRow(None, self.pDither)
        section.addRow(None, self.pAlpha)
        section.addRow(None, self.pUseThreshold)
        section.addRow(None, self.pThreshold)
        section.addRow(None, self.pUseBand)
        section.addRow("Keep from", self.pBandLow)
        section.addRow("up to", self.pBandHigh)
        self.pBandHint = section.addHint("")

        self.pLayout.addWidget(section)

    def pBuildEdges(self) -> None:
        section = Section("Edges")

        self.pEdges = QCheckBox("Draw edges with | / - \\")
        self.pEdges.setToolTip("Detect edges and draw them with directional characters (-e).")

        self.pEdgeSensitivity = SliderSpin(0, 100, 90)
        self.pEdgeSensitivity.setToolTip(
            "Percentile of gradient strength kept as edges (-et). Lower finds more."
        )

        section.addRow(None, self.pEdges)
        section.addRow("Sensitivity", self.pEdgeSensitivity)

        self.pLayout.addWidget(section)

    def pBuildAnimation(self) -> None:
        self.pAnimationSection = Section("Animation")
        section = self.pAnimationSection

        self.pUseMaxFrames = QCheckBox("Stop after")
        self.pMaxFrames = QSpinBox()
        self.pMaxFrames.setRange(1, 1_000_000)
        self.pMaxFrames.setValue(50)
        self.pMaxFrames.setSuffix(" frames")

        self.pFrameStep = QSpinBox()
        self.pFrameStep.setRange(1, 1000)
        self.pFrameStep.setValue(1)
        self.pFrameStep.setToolTip("Keep only every Nth frame (--framestep). Playback speed is preserved.")

        self.pUseFps = QCheckBox("Override frame rate")
        self.pFps = QDoubleSpinBox()
        self.pFps.setRange(0.1, 240.0)
        self.pFps.setValue(24.0)
        self.pFps.setSuffix(" fps")

        self.pWriteFrames = QCheckBox("Write every frame as its own file")
        self.pWriteFrames.setToolTip(
            "Puts numbered files in a folder beside the output (--frames). Needed to convert an "
            "animation to a single-frame format."
        )

        section.addRow(None, self.pUseMaxFrames)
        section.addRow(None, self.pMaxFrames)
        section.addRow("Keep every", self.pFrameStep)
        section.addRow(None, self.pUseFps)
        section.addRow(None, self.pFps)
        section.addRow(None, self.pWriteFrames)
        self.pAnimationHint = section.addHint("Load an animation or a video to use these.")

        self.pLayout.addWidget(section)

    def pBuildOutput(self) -> None:
        section = Section("Output")

        self.pOutputType = QComboBox()
        for name in tools.ValidTypes.asList():
            self.pOutputType.addItem(name.upper(), name)
        self.pOutputType.setCurrentIndex(self.pOutputType.findData('txt'))

        self.pEmbedColor = QCheckBox("Write colour into the text")
        self.pEmbedColor.setToolTip(
            "TXT and XML can carry colour alongside the characters. Off means characters only."
        )

        section.addRow("Format", self.pOutputType)
        section.addRow(None, self.pEmbedColor)
        self.pOutputHint = section.addHint("")

        self.pLayout.addWidget(section)

    def pBuildCompute(self) -> None:
        section = Section("Compute")

        self.pGpu = QComboBox()
        self.pGpu.addItem("CPU", None)
        for name in compute.BACKEND_CHOICES:
            self.pGpu.addItem(name, name)
        self.pGpu.setToolTip(
            "Needs CuPy or a GPU build of PyTorch installed. Neither ships with the tool, and "
            "without one this quietly falls back to the CPU."
        )

        section.addRow("Device", self.pGpu)

        self.pLayout.addWidget(section)

    # ================= Reacting ================

    def pWireSignals(self) -> None:
        for widget in (self.pWidthMode, self.pHeightMode, self.pOutputType,
                       self.pRampSize, self.pCharSet, self.pGpu):
            widget.currentIndexChanged.connect(self.pTouched)

        for widget in (self.pColored, self.pInvert, self.pDither, self.pAlpha, self.pEdges,
                       self.pUseThreshold, self.pUseBand, self.pLinkAspect, self.pUseMaxFrames,
                       self.pUseFps, self.pWriteFrames, self.pEmbedColor):
            widget.toggled.connect(self.pTouched)

        self.pBandLow.valueChanged.connect(self.pBandEdited)
        self.pBandHigh.valueChanged.connect(self.pBandEdited)

        for widget in (self.pMaxFrames, self.pFrameStep):
            widget.valueChanged.connect(self.pTouched)

        for widget in (self.pCharAspect, self.pFps):
            widget.valueChanged.connect(self.pTouched)

        for widget in (self.pThreshold, self.pEdgeSensitivity):
            widget.valueChanged.connect(self.pTouched)

        self.pCustomRamp.textChanged.connect(self.pTouched)

        for button in self.pModeButtons.values():
            button.toggled.connect(self.pTouched)

        self.pWidth.valueChanged.connect(self.pWidthEdited)
        self.pHeight.valueChanged.connect(self.pHeightEdited)

    def pTouched(self, *args) -> None:
        if self.pUpdating:
            return

        self.pSyncEnabled()
        self.changed.emit()

    def pBandEdited(self, value: int) -> None:
        """
        Keeps the two ends of the band from crossing over.

        Dragging the low end past the high one is a slip, not a request for an empty
        picture, so the other end is pushed along rather than the pair being left inverted.
        """
        if self.pUpdating:
            return

        self.pUpdating = True
        try:
            if self.sender() is self.pBandLow and self.pBandHigh.value() < value:
                self.pBandHigh.setValue(value)
            elif self.sender() is self.pBandHigh and self.pBandLow.value() > value:
                self.pBandLow.setValue(value)
        finally:
            self.pUpdating = False

        self.pTouched()

    def pWidthEdited(self, value: int) -> None:
        if self.pUpdating:
            return
        self.pMatchAspect(driver = 'width')
        self.pTouched()

    def pHeightEdited(self, value: int) -> None:
        if self.pUpdating:
            return
        self.pMatchAspect(driver = 'height')
        self.pTouched()

    def pMatchAspect(self, driver: str) -> None:
        """
        Works the other axis out from the one just edited.

        Same arithmetic the CLI's --auto uses, kept here rather than shared because the CLI
        applies it once to whatever the flags left missing, while the GUI applies it
        continuously to whichever box was not the one being typed in.
        """
        if not self.pLinkAspect.isChecked():
            return

        imgWidth, imgHeight = self.pImageSize
        if not imgWidth or not imgHeight:
            return

        # Only meaningful between two tile counts; a pixels-per-tile value is a different
        # quantity and relating the two by aspect would be nonsense.
        if self.pWidthMode.currentData() != 'count' or self.pHeightMode.currentData() != 'count':
            return

        aspect = self.pCharAspect.value()

        self.pUpdating = True
        try:
            if driver == 'width':
                wanted = round(self.pWidth.value() * aspect * imgHeight / imgWidth)
                self.pHeight.setValue(max(1, min(wanted, imgHeight)))
            else:
                wanted = round(self.pHeight.value() * imgWidth / (aspect * imgHeight))
                self.pWidth.setValue(max(1, min(wanted, imgWidth)))
        finally:
            self.pUpdating = False

    def pSyncEnabled(self) -> None:
        """Greys out whatever the current choices make meaningless."""
        mode = self.charMode()
        outputType = self.pOutputType.currentData()
        isText = outputType in ('txt', 'xml', 'svg')

        self.pRampSize.setEnabled(mode == 'rampSize')
        self.pCharSet.setEnabled(mode == 'charset')
        self.pCustomRamp.setEnabled(mode == 'customRamp')

        # Pixel art produces a picture directly, so nothing that shapes characters applies.
        forCharacters = mode != 'pixelart'
        self.pInvert.setEnabled(forCharacters)
        self.pUseThreshold.setEnabled(forCharacters)
        self.pThreshold.setEnabled(forCharacters and self.pUseThreshold.isChecked())
        self.pEdges.setEnabled(forCharacters)
        self.pEdgeSensitivity.setEnabled(forCharacters and self.pEdges.isChecked())

        # The band works on whole cells, so unlike the rest of this section it applies to
        # pixel art too, where it punches transparent holes instead of blanking characters.
        banding = self.pUseBand.isChecked()
        self.pBandLow.setEnabled(banding)
        self.pBandHigh.setEnabled(banding)
        self.pBandHint.setText(
            ("Outside this range: transparent blocks." if not forCharacters
             else "Outside this range: blank characters. Inside is untouched.")
            if banding else ""
        )

        selected = tools.CHARSETS.get(self.pCharSet.currentData()) if mode == 'charset' else None
        self.pDither.setEnabled(forCharacters and selected is not None and selected.isSubCell)

        carriesColorInline = outputType in ('txt', 'xml')
        self.pEmbedColor.setEnabled(self.pColored.isChecked() and carriesColorInline)

        # Colour with a text format is the one setting that can look like it does nothing:
        # TXT and XML only carry it if it is written into them, and otherwise the file is
        # identical with the box ticked or not. Say so, rather than letting it be a mystery.
        if self.pColored.isChecked() and carriesColorInline and not self.pEmbedColor.isChecked():
            self.pColourHint.setText(
                f"{outputType.upper()} keeps characters only until "
                f"'Write colour into the text' is on."
            )
        elif self.pColored.isChecked() and outputType == 'svg':
            self.pColourHint.setText("SVG always carries colour.")
        else:
            self.pColourHint.setText("")

        for widget in (self.pUseMaxFrames, self.pMaxFrames, self.pFrameStep,
                       self.pUseFps, self.pFps, self.pWriteFrames):
            widget.setEnabled(self.pIsAnimated)

        self.pMaxFrames.setEnabled(self.pIsAnimated and self.pUseMaxFrames.isChecked())
        self.pFps.setEnabled(self.pIsAnimated and self.pUseFps.isChecked())

        self.pCharAspect.setEnabled(self.pLinkAspect.isChecked())

        self.pCharsetHint.setText(selected.description if selected is not None else "")
        self.pOutputHint.setText(
            "Shown as text in the result pane." if isText else "Shown as a picture in the result pane."
        )

    # ================= State in and out ================

    def setSourceInfo(self, size: tuple[int, int], isAnimated: bool, frameCount: int) -> None:
        """Retunes the controls to a newly opened file."""
        self.pImageSize = size
        self.pIsAnimated = isAnimated

        imgWidth, imgHeight = size

        self.pUpdating = True
        try:
            self.pWidth.setMaximum(max(1, imgWidth))
            self.pHeight.setMaximum(max(1, imgHeight))
            self.pWidth.setValue(max(1, min(120, imgWidth)))
            self.pMaxFrames.setMaximum(max(1, frameCount))
        finally:
            self.pUpdating = False

        self.pMatchAspect(driver = 'width')

        self.pAnimationHint.setText(
            f"{frameCount} frames in this file." if isAnimated
            else "Load an animation or a video to use these."
        )
        self.pGridHint.setText(f"Source is {imgWidth} x {imgHeight} pixels.")

        self.pSyncEnabled()

    def charMode(self) -> str:
        for mode, button in self.pModeButtons.items():
            if button.isChecked():
                return mode

        return 'rampSize'

    def settings(self) -> dict:
        """
        Everything the panel is currently asking for, as plain values.

        A greyed out control reads as off, whatever its box happens to remember. Otherwise
        a setting the panel has already decided is meaningless — edge detection with pixel
        art, say — still reaches the config, and shows up in the command line the log
        prints as a flag that plainly is not doing anything.
        """
        def on(widget) -> bool:
            return widget.isChecked() and widget.isEnabled()

        animated = self.pIsAnimated

        return {
            'widthMode':        self.pWidthMode.currentData(),
            'widthValue':       self.pWidth.value(),
            'heightMode':       self.pHeightMode.currentData(),
            'heightValue':      self.pHeight.value(),
            'charAspect':       self.pCharAspect.value(),
            'charMode':         self.charMode(),
            'rampSize':         self.pRampSize.currentData(),
            'charsetName':      self.pCharSet.currentData(),
            'customRamp':       self.pCustomRamp.text(),
            'colored':          self.pColored.isChecked(),
            'invert':           on(self.pInvert),
            'dither':           on(self.pDither),
            'alpha':            self.pAlpha.isChecked(),
            'threshold':        self.pThreshold.value() if on(self.pUseThreshold) else None,
            'band':             ((self.pBandLow.value(), self.pBandHigh.value())
                                 if on(self.pUseBand) else None),
            'edges':            on(self.pEdges),
            'edgeSensitivity':  self.pEdgeSensitivity.value(),
            'maxFrames':        self.pMaxFrames.value() if animated and on(self.pUseMaxFrames) else None,
            'frameStep':        self.pFrameStep.value() if animated else 1,
            'fps':              self.pFps.value() if animated and on(self.pUseFps) else None,
            'writeFrames':      animated and on(self.pWriteFrames),
            'outputType':       self.pOutputType.currentData(),
            'embedColor':       on(self.pEmbedColor),
            'gpu':              self.pGpu.currentData(),
        }

    def setOutputType(self, name: str) -> None:
        """Used when the save dialog's chosen extension disagrees with the dropdown."""
        index = self.pOutputType.findData(name)
        if index >= 0:
            self.pOutputType.setCurrentIndex(index)
