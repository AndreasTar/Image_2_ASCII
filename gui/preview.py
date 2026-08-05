###########################################################################
# Copyright (c) 2024, Andy Pandy                                          #
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
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame, QGraphicsPixmapItem, QGraphicsScene, QGraphicsView, QHBoxLayout, QLabel,
    QPlainTextEdit, QSizePolicy, QSplitter, QStackedWidget, QVBoxLayout, QWidget,
)

# Zoom per wheel notch, and the range the user is allowed to reach.
ZOOM_STEP = 1.15
MIN_SCALE = 0.02
MAX_SCALE = 60.0


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

    def zoomBy(self, factor: float) -> None:
        target = self.scaleFactor() * factor
        if not MIN_SCALE <= target <= MAX_SCALE:
            return

        self.scale(factor, factor)
        self.pAnnounce()

    def copyViewFrom(self, other: 'ImageView') -> None:
        """
        Matches another view's zoom and scroll without reporting it back, which would
        otherwise bounce between the two panes forever.
        """
        self.pEmitting = False
        try:
            self.setTransform(other.transform())
            self.horizontalScrollBar().setValue(other.horizontalScrollBar().value())
            self.verticalScrollBar().setValue(other.verticalScrollBar().value())
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

        self.pResultText = QPlainTextEdit()
        self.pResultText.setObjectName('TextResult')
        self.pResultText.setReadOnly(True)
        self.pResultText.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

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
        keep = self.pResultStack.currentIndex() == 1 and self.pResultView.hasImage()

        self.pResultView.setImage(image, keepView = keep)
        self.pResultStack.setCurrentIndex(1)
        self.pResultPane.setTitle(label)

        if not keep:
            self.pMirror(self.pSourceView, self.pResultView)

    def setResultText(self, text: str, label: str = "RESULT") -> None:
        self.pResultText.setPlainText(text)
        self.pResultStack.setCurrentIndex(2)
        self.pResultPane.setTitle(label)

    def clearResult(self, message: str = "Convert to see the result here") -> None:
        self.pPlaceholder.setText(message)
        self.pResultStack.setCurrentIndex(0)
        self.pResultPane.setTitle("RESULT")

    # ---- framing ----

    def fitToWindow(self) -> None:
        self.pSourceView.fitToWindow()
        if self.pResultView.hasImage():
            self.pResultView.copyViewFrom(self.pSourceView)

    def zoomBy(self, factor: float) -> None:
        driver = self.pResultView if self.pResultStack.currentIndex() == 1 else self.pSourceView
        driver.zoomBy(factor)

    def pMirror(self, driver: ImageView, follower: ImageView) -> None:
        """
        Copies one view onto the other, but only while both are showing a picture of the
        same shape. A conversion can come out at a different size to its source, and
        forcing a shared transform across two different scene rectangles lines nothing up.
        """
        if not (driver.hasImage() and follower.hasImage()):
            return
        if driver.sceneRect().size() != follower.sceneRect().size():
            return

        follower.copyViewFrom(driver)
