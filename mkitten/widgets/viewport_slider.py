"""Viewport slider - a floating slider that appears above the mouse cursor.

Spawns a frameless widget in the Maya viewport with a horizontal slider,
an Apply (Enter) and Cancel (Escape) button. Multiple sliders can be
stacked on top of each other.
"""

from PySide6 import QtWidgets, QtCore, QtGui


class ViewportSlider(QtWidgets.QWidget):
    """A floating horizontal slider with Apply/Cancel buttons.

    Signals:
        value_changed(float): Emitted as the slider moves (0.0 - 1.0).
        applied(float): Emitted when Enter is pressed or Apply clicked.
        cancelled(): Emitted when Escape is pressed or Cancel clicked.

    Usage::

        slider = ViewportSlider("Blend", min_val=0.0, max_val=1.0)
        slider.value_changed.connect(my_callback)
        slider.applied.connect(on_apply)
        slider.cancelled.connect(on_cancel)
        slider.show()
    """

    value_changed = QtCore.Signal(float)
    applied = QtCore.Signal(float)
    cancelled = QtCore.Signal()

    # Track all active sliders for stacking
    _active_sliders = []

    SLIDER_WIDTH = 250
    SLIDER_HEIGHT = 32

    def __init__(self, label="", min_val=0.0, max_val=1.0, default=1.0,
                 steps=100, parent=None):
        # Parent to Maya's main window so it stays on top
        if parent is None:
            parent = _get_maya_main_window()
        super().__init__(parent, QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        self._min_val = min_val
        self._max_val = max_val
        self._steps = steps
        self._label = label

        # -- Build UI --
        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(6, 4, 6, 4)
        main_layout.setSpacing(6)

        # Container for styling
        self._container = QtWidgets.QFrame(self)
        self._container.setStyleSheet(
            "QFrame {"
            "  background: rgba(40, 40, 40, 230);"
            "  border: 1px solid rgba(80, 80, 80, 200);"
            "  border-radius: 6px;"
            "}"
        )
        container_layout = QtWidgets.QHBoxLayout(self._container)
        container_layout.setContentsMargins(8, 4, 8, 4)
        container_layout.setSpacing(6)

        # Label (acts as drag handle)
        if label:
            lbl = QtWidgets.QLabel(label)
            lbl.setStyleSheet(
                "color: #ccc; font-size: 11px; background: transparent;"
                "border: none; cursor: move;"
            )
            lbl.setCursor(QtCore.Qt.OpenHandCursor)
            lbl.installEventFilter(self)
            container_layout.addWidget(lbl)

        self._drag_start_pos = None
        self._drag_start_widget_pos = None

        # Slider
        self._slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self._slider.setRange(0, steps)
        self._slider.setValue(int((default - min_val) / (max_val - min_val) * steps))
        self._slider.setTracking(True)
        self._slider.setMinimumWidth(120)
        self._slider.setStyleSheet(
            "QSlider { background: transparent; border: none; }"
            "QSlider::groove:horizontal {"
            "  height: 6px; background: rgba(60, 60, 60, 200); border-radius: 3px;"
            "}"
            "QSlider::handle:horizontal {"
            "  width: 14px; height: 14px; margin: -4px 0;"
            "  background: #8af; border-radius: 7px;"
            "}"
        )
        self._slider.valueChanged.connect(self._on_slider_changed)
        container_layout.addWidget(self._slider)

        # Value display
        self._value_label = QtWidgets.QLabel(self._format_value(default))
        self._value_label.setMinimumWidth(35)
        self._value_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self._value_label.setStyleSheet(
            "color: #8af; font-size: 11px; background: transparent; border: none;"
        )
        container_layout.addWidget(self._value_label)

        # Apply button
        apply_btn = QtWidgets.QPushButton("\u2713")
        apply_btn.setFixedSize(22, 22)
        apply_btn.setToolTip("Apply (Enter)")
        apply_btn.setStyleSheet(
            "QPushButton {"
            "  background: rgba(80, 160, 80, 180); color: white;"
            "  border: none; border-radius: 4px; font-weight: bold;"
            "}"
            "QPushButton:hover { background: rgba(100, 200, 100, 220); }"
        )
        apply_btn.clicked.connect(self._apply)
        container_layout.addWidget(apply_btn)

        # Cancel button
        cancel_btn = QtWidgets.QPushButton("\u2717")
        cancel_btn.setFixedSize(22, 22)
        cancel_btn.setToolTip("Cancel (Esc)")
        cancel_btn.setStyleSheet(
            "QPushButton {"
            "  background: rgba(160, 80, 80, 180); color: white;"
            "  border: none; border-radius: 4px; font-weight: bold;"
            "}"
            "QPushButton:hover { background: rgba(200, 100, 100, 220); }"
        )
        cancel_btn.clicked.connect(self._cancel)
        container_layout.addWidget(cancel_btn)

        main_layout.addWidget(self._container)

        self.adjustSize()

    def eventFilter(self, obj, event):
        """Handle dragging from the label."""
        if event.type() == QtCore.QEvent.MouseButtonPress:
            if event.button() == QtCore.Qt.LeftButton:
                self._drag_start_pos = event.globalPosition().toPoint()
                self._drag_start_widget_pos = self.pos()
                obj.setCursor(QtCore.Qt.ClosedHandCursor)
                return True

        elif event.type() == QtCore.QEvent.MouseMove:
            if self._drag_start_pos is not None:
                delta = event.globalPosition().toPoint() - self._drag_start_pos
                self.move(self._drag_start_widget_pos + delta)
                return True

        elif event.type() == QtCore.QEvent.MouseButtonRelease:
            if self._drag_start_pos is not None:
                self._drag_start_pos = None
                obj.setCursor(QtCore.Qt.OpenHandCursor)
                return True

        return False

    def _format_value(self, val):
        return f"{val:.0%}" if self._max_val == 1.0 else f"{val:.2f}"

    def _to_value(self, slider_val):
        """Convert integer slider position to float value."""
        t = slider_val / self._steps
        return self._min_val + t * (self._max_val - self._min_val)

    def _on_slider_changed(self, slider_val):
        val = self._to_value(slider_val)
        self._value_label.setText(self._format_value(val))
        self.value_changed.emit(val)

    def get_value(self):
        return self._to_value(self._slider.value())

    def _apply(self):
        self.applied.emit(self.get_value())
        self._close_slider()

    def _cancel(self):
        self.cancelled.emit()
        self._close_slider()

    def _close_slider(self):
        if self in ViewportSlider._active_sliders:
            ViewportSlider._active_sliders.remove(self)
            _restack_sliders()
        self.close()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Return or event.key() == QtCore.Qt.Key_Enter:
            self._apply()
        elif event.key() == QtCore.Qt.Key_Escape:
            self._cancel()
        else:
            super().keyPressEvent(event)

    def show_at_cursor(self):
        """Show the slider above the mouse cursor, stacking with others."""
        ViewportSlider._active_sliders.append(self)
        self.show()
        _restack_sliders()
        self.setFocus()

    def closeEvent(self, event):
        if self in ViewportSlider._active_sliders:
            ViewportSlider._active_sliders.remove(self)
            _restack_sliders()
        super().closeEvent(event)


def _get_maya_main_window():
    """Get Maya's main window as a QWidget."""
    import maya.OpenMayaUI as omui
    from shiboken6 import wrapInstance
    ptr = omui.MQtUtil.mainWindow()
    if ptr is not None:
        return wrapInstance(int(ptr), QtWidgets.QWidget)
    return None


def _restack_sliders():
    """Reposition all active sliders stacked above the original cursor pos."""
    if not ViewportSlider._active_sliders:
        return

    cursor_pos = QtGui.QCursor.pos()
    spacing = 4

    # Stack from bottom (closest to cursor) to top
    for i, slider in enumerate(reversed(ViewportSlider._active_sliders)):
        x = cursor_pos.x() - slider.width() // 2
        y = cursor_pos.y() - (i + 1) * (slider.height() + spacing)
        slider.move(x, y)


def close_all():
    """Close all active viewport sliders."""
    for slider in list(ViewportSlider._active_sliders):
        slider.cancelled.emit()
        slider.close()
    ViewportSlider._active_sliders.clear()
