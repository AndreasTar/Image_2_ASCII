###########################################################################
# Copyright (c) 2024-2026, Andy Pandy                                          #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################

"""
How the window looks.

Qt's stock widgets follow the platform theme, which on Windows still draws boxy nineties
controls. Everything here is one stylesheet over the top of them, in two palettes that
differ only in their colour values, so the light and dark versions cannot drift apart in
layout or spacing the way two hand written sheets would.
"""

import atexit
import pathlib as pl
import shutil
import tempfile

from PIL import Image, ImageDraw
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication, QPalette

DARK = {
    'bg':           '#0f1116',
    'surface':      '#171a21',
    'surfaceHigh':  '#1e222b',
    'border':       '#282d38',
    'borderStrong': '#3a4150',
    'text':         '#e7e9ee',
    'textMuted':    '#8b93a3',
    'accent':       '#5b8cff',
    'accentHover':  '#729dff',
    'accentText':   '#ffffff',
    'danger':       '#ff6b6b',
    'ok':           '#4ade80',
    'canvas':       '#0b0d11',
}

LIGHT = {
    'bg':           '#f4f5f8',
    'surface':      '#ffffff',
    'surfaceHigh':  '#f0f2f6',
    'border':       '#dde1e8',
    'borderStrong': '#c3cad6',
    'text':         '#1a1d24',
    'textMuted':    '#666e7d',
    'accent':       '#3b6fe0',
    'accentHover':  '#3364d4',
    'accentText':   '#ffffff',
    'danger':       '#d64545',
    'ok':           '#2f9e5e',
    'canvas':       '#e8eaef',
}

# The preview panes draw their own background, so they need the values rather than the
# stylesheet. Everything else is styled through the sheet below.
MONOSPACE = 'Cascadia Mono, Consolas, DejaVu Sans Mono, Menlo, monospace'


pArrowDir: pl.Path | None = None


def pChevron(colour: str) -> str:
    """
    --- Private method! ---\n
    Draws the dropdown chevron and returns a path a stylesheet can point at.

    Qt hands a styled combo box's arrow back to the stylesheet, and a stylesheet can only
    name an image by URL, so the arrow has to exist as a file somewhere. Drawing it with
    Pillow, which the tool already depends on, means no image to ship, nothing to add to
    the build, and an arrow that is exactly the palette's own colour.

    A data URI would avoid the file, but Qt's parser gives up on the angle brackets in an
    inline SVG and silently discards every rule after it.
    """
    global pArrowDir

    if pArrowDir is None:
        pArrowDir = pl.Path(tempfile.mkdtemp(prefix = 'image2ascii-ui-'))
        atexit.register(shutil.rmtree, pArrowDir, True)

    target = pArrowDir / f"chevron-{colour.lstrip('#')}.png"

    if not target.exists():
        # Drawn at four times the size and scaled down, which is the cheapest way to get a
        # smooth diagonal out of Pillow's aliased line drawing.
        scale, size = 4, 10
        canvas = Image.new('RGBA', (size * scale, size * scale), (0, 0, 0, 0))
        pen = ImageDraw.Draw(canvas)
        pen.line(
            [(2 * scale, 4 * scale), (5 * scale, 7 * scale), (8 * scale, 4 * scale)],
            fill = colour, width = int(1.4 * scale), joint = 'curve',
        )
        canvas.resize((size, size), Image.LANCZOS).save(target)

    # Qt wants forward slashes in a stylesheet URL on every platform, Windows included.
    return target.as_posix()


def currentPalette() -> dict:
    """Whichever palette matches the desktop's own light or dark setting."""
    hints = QGuiApplication.styleHints()

    scheme = getattr(hints, 'colorScheme', None)
    if scheme is not None and scheme() == Qt.ColorScheme.Light:
        return LIGHT

    return DARK


def stylesheet(palette: dict) -> str:
    """The whole application sheet, with one palette's colours substituted in."""
    return _SHEET % palette


def apply(app, palette: dict | None = None) -> dict:
    """
    Dresses the application: Fusion underneath, the sheet above, and a matching Qt palette.

    Fusion rather than the native Windows style because the sub-controls a stylesheet does
    not cover, like dropdown arrows, menu chevrons, are drawn by the style itself, and the
    native one draws them in system colours that vanish against a dark sheet. Fusion takes
    its colours from the palette set here, so those loose ends come out right too.
    """
    if palette is None:
        palette = currentPalette()

    # Drawn now rather than at import time, so that nothing touches the filesystem just
    # because this module was imported.
    palette = dict(palette)
    palette['arrow'] = pChevron(palette['text'])
    palette['arrowMuted'] = pChevron(palette['textMuted'])

    app.setStyle('Fusion')
    app.setPalette(pQtPalette(palette))
    app.setStyleSheet(stylesheet(palette))

    return palette


def pQtPalette(palette: dict) -> QPalette:
    """
    --- Private method! ---\n
    The same colours again, as the object the style consults rather than the sheet.
    """
    qt = QPalette()
    text = QColor(palette['text'])
    muted = QColor(palette['textMuted'])

    for role, colour in (
        (QPalette.ColorRole.Window,          QColor(palette['bg'])),
        (QPalette.ColorRole.WindowText,      text),
        (QPalette.ColorRole.Base,            QColor(palette['bg'])),
        (QPalette.ColorRole.AlternateBase,   QColor(palette['surface'])),
        (QPalette.ColorRole.Text,            text),
        (QPalette.ColorRole.Button,          QColor(palette['surfaceHigh'])),
        (QPalette.ColorRole.ButtonText,      text),
        (QPalette.ColorRole.Highlight,       QColor(palette['accent'])),
        (QPalette.ColorRole.HighlightedText, QColor(palette['accentText'])),
        (QPalette.ColorRole.ToolTipBase,     QColor(palette['surfaceHigh'])),
        (QPalette.ColorRole.ToolTipText,     text),
        (QPalette.ColorRole.PlaceholderText, muted),
    ):
        qt.setColor(role, colour)

    for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text,
                 QPalette.ColorRole.ButtonText):
        qt.setColor(QPalette.ColorGroup.Disabled, role, muted)

    return qt


# Written as one template with named substitutions rather than f-strings, because Qt
# stylesheets are full of braces and doubling every one of them makes this unreadable.
_SHEET = """
QWidget {
    background: %(bg)s;
    color: %(text)s;
    font-family: 'Segoe UI', 'Inter', 'SF Pro Text', system-ui, sans-serif;
    font-size: 13px;
}

QMainWindow, QDialog { background: %(bg)s; }

QToolTip {
    background: %(surfaceHigh)s;
    color: %(text)s;
    border: 1px solid %(borderStrong)s;
    border-radius: 6px;
    padding: 6px 8px;
}

/* ---------- Sections ---------- */

QFrame#Card {
    background: %(surface)s;
    border: 1px solid %(border)s;
    border-radius: 10px;
}

QLabel#SectionTitle {
    color: %(textMuted)s;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    padding: 2px 0;
}

QLabel#Hint {
    color: %(textMuted)s;
    font-size: 11px;
}

QLabel#PaneTitle {
    color: %(textMuted)s;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    padding: 6px 10px;
}

QLabel#Placeholder {
    color: %(textMuted)s;
    font-size: 13px;
}

QFrame#Separator {
    background: %(border)s;
    max-height: 1px;
    border: none;
}

/* ---------- Buttons ---------- */

QPushButton {
    background: %(surfaceHigh)s;
    color: %(text)s;
    border: 1px solid %(border)s;
    border-radius: 8px;
    padding: 7px 14px;
    font-weight: 600;
}
QPushButton:hover  { border-color: %(borderStrong)s; }
QPushButton:pressed { background: %(surface)s; }
QPushButton:disabled { color: %(textMuted)s; border-color: %(border)s; }

QPushButton#Primary {
    background: %(accent)s;
    color: %(accentText)s;
    border: 1px solid %(accent)s;
}
QPushButton#Primary:hover   { background: %(accentHover)s; border-color: %(accentHover)s; }
QPushButton#Primary:disabled { background: %(surfaceHigh)s; color: %(textMuted)s; border-color: %(border)s; }

/* ---------- Text entry ---------- */

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit {
    background: %(bg)s;
    color: %(text)s;
    border: 1px solid %(border)s;
    border-radius: 7px;
    padding: 6px 9px;
    selection-background-color: %(accent)s;
    selection-color: %(accentText)s;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QPlainTextEdit:focus {
    border-color: %(accent)s;
}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {
    color: %(textMuted)s;
    background: %(surface)s;
}

QLineEdit#Ramp, QPlainTextEdit#Log, QPlainTextEdit#TextResult {
    font-family: %(mono)s;
}

QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {
    width: 0; height: 0; border: none; background: none;
}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow,
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow { width: 0; height: 0; image: none; }

QComboBox::drop-down { border: none; width: 24px; }
QComboBox::down-arrow {
    image: url(%(arrow)s);
    width: 10px;
    height: 10px;
    margin-right: 9px;
}
QComboBox::down-arrow:disabled { image: url(%(arrowMuted)s); }
QComboBox QAbstractItemView {
    background: %(surfaceHigh)s;
    color: %(text)s;
    border: 1px solid %(borderStrong)s;
    border-radius: 8px;
    padding: 4px;
    outline: none;
    selection-background-color: %(accent)s;
    selection-color: %(accentText)s;
}

/* ---------- Toggles ---------- */

QCheckBox, QRadioButton { spacing: 8px; padding: 3px 0; }
QCheckBox::indicator, QRadioButton::indicator { width: 17px; height: 17px; }

QCheckBox::indicator {
    border: 1px solid %(borderStrong)s;
    border-radius: 5px;
    background: %(bg)s;
}
QCheckBox::indicator:hover { border-color: %(accent)s; }
/* Filled rather than ticked. A tick means an inline SVG, and a `url(data:...)` with raw
   angle brackets in it stops Qt's stylesheet parser dead: every rule after the one it
   chokes on is silently dropped, which cost the sliders and scrollbars their styling. */
QCheckBox::indicator:checked {
    background: %(accent)s;
    border: 4px solid %(bg)s;
    border-radius: 5px;
}
QCheckBox:disabled, QRadioButton:disabled { color: %(textMuted)s; }

QRadioButton::indicator {
    border: 1px solid %(borderStrong)s;
    border-radius: 9px;
    background: %(bg)s;
}
QRadioButton::indicator:hover { border-color: %(accent)s; }
QRadioButton::indicator:checked {
    background: %(accent)s;
    border: 5px solid %(bg)s;
    border-radius: 9px;
}

/* ---------- Sliders ---------- */

QSlider::groove:horizontal {
    height: 4px;
    background: %(surfaceHigh)s;
    border: 1px solid %(border)s;
    border-radius: 3px;
}
QSlider::sub-page:horizontal { background: %(accent)s; border-radius: 3px; }
QSlider::handle:horizontal {
    background: %(text)s;
    width: 14px;
    height: 14px;
    margin: -6px 0;
    border-radius: 7px;
}
QSlider::handle:horizontal:hover { background: %(accent)s; }
QSlider:disabled::sub-page:horizontal { background: %(borderStrong)s; }

/* ---------- Progress ---------- */

QProgressBar {
    background: %(surfaceHigh)s;
    border: 1px solid %(border)s;
    border-radius: 7px;
    height: 6px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk { background: %(accent)s; border-radius: 6px; }

/* ---------- Scrolling ---------- */

QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; border: none; }

QScrollBar:vertical   { background: transparent; width: 10px; margin: 2px; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: %(borderStrong)s;
    border-radius: 5px;
    min-height: 30px;
    min-width: 30px;
}
QScrollBar::handle:hover { background: %(textMuted)s; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: none; }

/* ---------- Splitter ---------- */

QSplitter::handle { background: %(border)s; }
QSplitter::handle:horizontal { width: 1px; }
QSplitter::handle:vertical   { height: 1px; }

/* ---------- Preview ---------- */

QGraphicsView { background: %(canvas)s; border: none; }

QFrame#Pane {
    background: %(surface)s;
    border: 1px solid %(border)s;
    border-radius: 10px;
}

QPlainTextEdit#TextResult, QPlainTextEdit#Log {
    background: %(canvas)s;
    border: none;
    border-radius: 0;
    font-size: 12px;
}

QStatusBar { background: %(surface)s; color: %(textMuted)s; border-top: 1px solid %(border)s; }
QStatusBar::item { border: none; }
"""

# The monospace stack is shared with the preview, so it is folded into the palette rather
# than repeated in the sheet.
DARK['mono'] = MONOSPACE
LIGHT['mono'] = MONOSPACE
