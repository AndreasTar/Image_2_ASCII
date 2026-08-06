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
The before and after panes.

Comparing an ASCII conversion against its source only means anything if both are showing
the same part of the picture at the same magnification, so the two views share a zoom and
a scroll position. Getting a character to line up with the pixels it came from is most of
the value of having a preview at all.
"""

import io

from PIL import Image
from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QFont, QFontMetricsF, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame, QGraphicsPixmapItem, QGraphicsScene, QGraphicsView, QHBoxLayout, QLabel,
    QPlainTextEdit, QSizePolicy, QSplitter, QStackedWidget, QVBoxLayout, QWidget,
)

# Zoom per wheel notch.
ZOOM_STEP = 1.15

# How far out and in the zoom may go, both measured against the scale at which the whole
# picture fits the pane. Fixed limits cannot work here: a 2000 pixel photograph and a 60
# character conversion of it fit at wildly different scales, so the same absolute number is
# either useless or unreachable depending on which is being looked at.
#
# Out is capped just past 'the whole thing', which leaves a little breathing space around
# the picture without letting it shrink into a speck. In is capped well past 1:1, which for
# a conversion means far enough to read one character comfortably.
MIN_ZOOM_OF_FIT = 0.9
MAX_ZOOM_OF_FIT = 80.0


def toPixmap(image: Image.Image) -> QPixmap:
    """
    A Pillow image as something Qt can draw.

    Goes through an in-memory PNG rather than `PIL.ImageQt`, which needs Pillow to have
    been built against a specific Qt binding. This way works with whatever is installed,
    and leaves one less thing that can break in a frozen build.
    """
    buffer = io.BytesIO()
    image.save(buffer, format = 'PNG')

    pixmap = QPixmap()
    pixmap.loadFromData(buffer.getvalue(), 'PNG')

    return pixmap


class ImageView(QGraphicsView):
    """
    One pannable, zoomable picture.

    Reports the view transform whenever it changes so a peer can copy it. Nothing here
    knows about the peer itself, which keeps the syncing to one place in `PreviewPane`.
    """

    viewChanged = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setScene(QGraphicsScene(self))
        self.pItem = QGraphicsPixmapItem()
        self.scene().addItem(self.pItem)

        self.setRenderHints(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)

        self.pEmitting = True
        self.horizontalScrollBar().valueChanged.connect(self.pAnnounce)
        self.verticalScrollBar().valueChanged.connect(self.pAnnounce)

    # ---- content ----

    def setImage(self, image: Image.Image | None, keepView: bool = False) -> None:
        """
        Shows a picture, fitting it to the pane unless the caller wants the current
        framing kept. Keeping it is what makes re-converting at a new setting feel like
        the picture changed underneath a fixed camera, rather than a jump.
        """
        if image is None:
            self.pItem.setPixmap(QPixmap())
            return

        pixmap = toPixmap(image)
        hadContent = not self.pItem.pixmap().isNull()

        self.pItem.setPixmap(pixmap)
        self.setSceneRect(QRectF(pixmap.rect()))

        if not (keepView and hadContent):
            self.fitToWindow()

    def hasImage(self) -> bool:
        return not self.pItem.pixmap().isNull()

    # ---- framing ----

    def fitToWindow(self) -> None:
        if not self.hasImage():
            return

        self.fitInView(self.pItem, Qt.AspectRatioMode.KeepAspectRatio)
        self.pAnnounce()

    def scaleFactor(self) -> float:
        return self.transform().m11()

    def fitScale(self) -> float:
        """The scale at which the whole picture just fits the pane."""
        if not self.hasImage():
            return 1.0

        scene = self.sceneRect()
        viewport = self.viewport().rect()

        if not scene.width() or not scene.height():
            return 1.0

        return min(viewport.width() / scene.width(), viewport.height() / scene.height())

    def zoomBy(self, factor: float) -> None:
        """
        Zooms, stopping at the limits rather than refusing the whole step at the edge.

        Clamping the factor instead of rejecting it means a wheel notch near the end still
        travels the remaining distance, so the zoom arrives exactly at the limit instead of
        sticking short of it.
        """
        if not self.hasImage():
            return

        fit = self.fitScale()
        current = self.scaleFactor()
        target = min(max(current * factor, fit * MIN_ZOOM_OF_FIT), fit * MAX_ZOOM_OF_FIT)

        if abs(target - current) < 1e-9:
            return

        self.scale(target / current, target / current)
        self.pAnnounce()

    def visibleFraction(self) -> tuple[float, float, float, float]:
        """
        Which part of the picture is on screen, as fractions of the whole.

        Expressed as a proportion rather than in pixels so that it means something to a
        view showing a differently sized picture. A 60x30 character conversion and the
        2000 pixel photograph it came from have no coordinates in common, but 'the middle
        third' is the same place in both.
        """
        scene = self.sceneRect()
        visible = self.mapToScene(self.viewport().rect()).boundingRect()

        width = scene.width() or 1.0
        height = scene.height() or 1.0

        return (
            (visible.left() - scene.left()) / width,
            (visible.top() - scene.top()) / height,
            visible.width() / width,
            visible.height() / height,
        )

    def showFraction(self, fraction: tuple[float, float, float, float]) -> None:
        """
        Frames the same proportion of this picture, without reporting it back, which
        would otherwise bounce between the two panes forever.
        """
        left, top, width, height = fraction
        scene = self.sceneRect()

        target = QRectF(
            scene.left() + left * scene.width(),
            scene.top() + top * scene.height(),
            max(width * scene.width(), 1e-6),
            max(height * scene.height(), 1e-6),
        )

        self.pEmitting = False
        try:
            self.fitInView(target, Qt.AspectRatioMode.KeepAspectRatio)
        finally:
            self.pEmitting = True

    def pAnnounce(self) -> None:
        if self.pEmitting:
            self.viewChanged.emit()

    # ---- events ----

    def wheelEvent(self, event) -> None:
        self.zoomBy(ZOOM_STEP if event.angleDelta().y() > 0 else 1 / ZOOM_STEP)

    def mouseDoubleClickEvent(self, event) -> None:
        self.fitToWindow()


class TextView(QPlainTextEdit):
    """
    The characters themselves, sized to fit the pane.

    An ASCII conversion is a fixed grid, and a fixed point size cannot show one: a hundred
    and twenty columns overflow a pane that ninety would have fitted, and the result is a
    picture the user cannot see the shape of. The font is scaled instead, so 'fit' means
    the same thing here as it does for the picture beside it.
    """

    # Sizes the fitting is allowed to land on. Below the minimum the characters stop being
    # distinguishable at all, so a very wide conversion scrolls rather than turning to dust.
    MIN_POINT = 1.0
    MAX_POINT = 72.0
    REFERENCE_POINT = 40.0

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setObjectName('TextResult')
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.pColumns = 0
        self.pRows = 0
        # Stays true until the user zooms by hand, at which point resizing the window should
        # no longer quietly undo their choice.
        self.pAutoFit = True

    def setText(self, text: str) -> None:
        lines = text.splitlines() or ['']

        self.pColumns = max(len(line) for line in lines)
        self.pRows = len(lines)
        self.pAutoFit = True

        self.setPlainText(text)
        self.fitToWindow()

    def fitToWindow(self) -> None:
        self.pAutoFit = True
        self.pApplyPointSize(self.pPointSizeThatFits())

    def zoomBy(self, factor: float) -> None:
        self.pAutoFit = False
        self.pApplyPointSize(self.font().pointSizeF() * factor)

    def pFitsAt(self, size: float, usableWidth: float, usableHeight: float) -> bool:
        """
        --- Private method! ---\n
        Whether the whole grid would be visible at this exact point size.
        """
        probe = QFont(self.font())
        probe.setPointSizeF(size)
        metrics = QFontMetricsF(probe)

        return (metrics.horizontalAdvance('M') * self.pColumns <= usableWidth
                and metrics.lineSpacing() * self.pRows <= usableHeight)

    def pPointSizeThatFits(self) -> float:
        """
        The largest point size at which the whole grid is visible.

        Found by bisection, measuring at each candidate size rather than by measuring once
        and scaling. Advance width is very nearly proportional to point size, but not quite:
        a font hints its glyphs onto whole pixels, so at the small sizes a wide conversion
        needs, the rounding is a large enough fraction of the advance to push the text back
        over the edge of the pane. Measuring where the answer actually lands avoids that.
        """
        if not self.pColumns or not self.pRows:
            return self.font().pointSizeF()

        # The document sits inside the frame with a margin at each side, and a scrollbar
        # would otherwise appear exactly when the text had been made to fit without one.
        available = self.viewport().size()
        usableWidth = max(available.width() - 2 * self.document().documentMargin() - 2, 1)
        usableHeight = max(available.height() - 2 * self.document().documentMargin() - 2, 1)

        if not self.pFitsAt(self.MIN_POINT, usableWidth, usableHeight):
            return self.MIN_POINT

        low, high = self.MIN_POINT, self.MAX_POINT
        for _ in range(24):
            middle = (low + high) / 2
            if self.pFitsAt(middle, usableWidth, usableHeight):
                low = middle
            else:
                high = middle

        return low

    def pApplyPointSize(self, size: float) -> None:
        font = QFont(self.font())
        font.setPointSizeF(min(max(size, self.MIN_POINT), self.MAX_POINT))

        self.setFont(font)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)

        if self.pAutoFit:
            self.pApplyPointSize(self.pPointSizeThatFits())


class Pane(QFrame):
    """A titled box around one view, so the two sides read as a pair."""

    def __init__(self, title: str, body: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName('Pane')

        self.pTitle = QLabel(title)
        self.pTitle.setObjectName('PaneTitle')

        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)
        layout.addWidget(self.pTitle)
        layout.addWidget(body, 1)

    def setTitle(self, title: str) -> None:
        self.pTitle.setText(title)


class PreviewPane(QWidget):
    """
    Source on the left, result on the right, sharing one camera.

    The result side swaps between a picture and a block of text, because half the output
    formats are characters rather than an image and rendering those to a bitmap just to
    show them would misrepresent what the tool actually produced.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.pSourceView = ImageView()
        self.pResultView = ImageView()

        self.pResultText = TextView()

        self.pPlaceholder = QLabel("Open an image to get started")
        self.pPlaceholder.setObjectName('Placeholder')
        self.pPlaceholder.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.pResultStack = QStackedWidget()
        self.pResultStack.addWidget(self.pPlaceholder)   # 0
        self.pResultStack.addWidget(self.pResultView)    # 1
        self.pResultStack.addWidget(self.pResultText)    # 2

        self.pSourcePane = Pane("SOURCE", self.pSourceView)
        self.pResultPane = Pane("RESULT", self.pResultStack)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self.pSourcePane)
        split.addWidget(self.pResultPane)
        split.setSizes([500, 500])
        split.setChildrenCollapsible(False)
        split.setHandleWidth(8)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(split)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.pSourceView.viewChanged.connect(lambda: self.pMirror(self.pSourceView, self.pResultView))
        self.pResultView.viewChanged.connect(lambda: self.pMirror(self.pResultView, self.pSourceView))

    # ---- content ----

    def setSource(self, image: Image.Image | None, label: str = "SOURCE") -> None:
        self.pSourceView.setImage(image)
        self.pSourcePane.setTitle(label)

    def setResultImage(self, image: Image.Image, label: str = "RESULT") -> None:
        # A conversion that only differs by a setting should not throw away where the user
        # was looking, so the framing is kept whenever a picture is replacing a picture.
        wasShowingPicture = self.pResultStack.currentIndex() == 1 and self.pResultView.hasImage()
        framing = self.pResultView.visibleFraction() if wasShowingPicture else None

        self.pResultView.setImage(image)
        self.pResultStack.setCurrentIndex(1)
        self.pResultPane.setTitle(label)

        if framing is not None:
            self.pResultView.showFraction(framing)
        else:
            self.pMirror(self.pSourceView, self.pResultView)

    def setResultText(self, text: str, label: str = "RESULT") -> None:
        self.pResultText.setText(text)
        self.pResultStack.setCurrentIndex(2)
        self.pResultPane.setTitle(label)

    def clearResult(self, message: str = "Convert to see the result here") -> None:
        self.pPlaceholder.setText(message)
        self.pResultStack.setCurrentIndex(0)
        self.pResultPane.setTitle("RESULT")

    # ---- framing ----

    def fitToWindow(self) -> None:
        """
        Frames everything in full.

        Each pane is fitted to its own contents rather than one being fitted and the other
        copying it. The two pictures are rarely the same size, and copying a framing that
        suits a 2000 pixel photograph to a 600 pixel conversion is what left the result
        sitting small in the middle of its pane.
        """
        self.pSourceView.fitToWindow()
        self.pResultView.fitToWindow()
        self.pResultText.fitToWindow()

    def zoomBy(self, factor: float) -> None:
        if self.pResultStack.currentIndex() == 2:
            self.pResultText.zoomBy(factor)
            return

        driver = self.pResultView if self.pResultView.hasImage() else self.pSourceView
        driver.zoomBy(factor)

    def pMirror(self, driver: ImageView, follower: ImageView) -> None:
        """
        Points the other pane at the same part of its own picture.

        What is shared is the *region*, as a proportion of each picture, not the transform.
        Sharing the transform only ever worked when both sides happened to be the same size,
        which in practice meant pixel art and nothing else: every character based conversion
        comes out at its own resolution, so the two scene rectangles disagreed and the sync
        gave up rather than lining anything up.
        """
        if not (driver.hasImage() and follower.hasImage()):
            return

        follower.showFraction(driver.visibleFraction())
