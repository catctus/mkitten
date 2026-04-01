"""ToolGroup variants with hotkey display and status indicator in the header."""

from PySide6 import QtWidgets, QtCore, QtGui

from mkitten import hotkeys


class _StatusIndicator(QtWidgets.QWidget):
    """Small colored square that shows enabled/disabled state.

    Right-click to toggle this individual hotkey on/off.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(12, 12)
        self._enabled = True
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setToolTip("Toggle shortcut on/off")

    def set_enabled(self, enabled):
        self._enabled = enabled
        self.update()

    def is_enabled(self):
        return self._enabled

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setPen(QtCore.Qt.NoPen)
        color = QtGui.QColor("#5a5") if self._enabled else QtGui.QColor("#a55")
        painter.setBrush(color)
        painter.drawRoundedRect(self.rect(), 2, 2)
        painter.end()


class _HotkeyHeaderMixin:
    """Mixin providing hotkey label, indicator, and toggle logic.

    Expects the subclass to set self._action_id before calling
    _build_hotkey_header_widgets().
    """

    def _build_hotkey_header_widgets(self, top_row):
        """Add hotkey label and status indicator to a QHBoxLayout row."""
        # Hotkey label
        self._hotkey_label = QtWidgets.QLabel("")
        self._hotkey_label.setStyleSheet(
            "font-size: 11px;"
            "color: #ccc;"
            "background: rgba(0, 0, 0, 60);"
            "padding: 2px 6px;"
            "border-radius: 3px;"
        )
        top_row.addWidget(self._hotkey_label)

        # Status indicator (right-click to toggle)
        self._indicator = _StatusIndicator()
        self._indicator.installEventFilter(self)
        top_row.addWidget(self._indicator)

    def _build_status_label(self, header_layout, default_text=""):
        """Add a status/description line to the header layout.

        Shows default_text initially, then updates with status messages
        via set_status().
        """
        self._default_status_text = default_text
        self._status_label = QtWidgets.QLabel(default_text)
        self._status_label.setStyleSheet(
            "font-size: 11px; color: palette(light); background: transparent;"
        )
        self._status_label.setVisible(bool(default_text))
        header_layout.addWidget(self._status_label)

    def set_status(self, text, status="info"):
        """Set the status text shown in the header.

        Args:
            text: The message to display. Empty string reverts to default
                description.
            status: "info" (default/gray), "success" (green), or "error" (red).
        """
        if text:
            colors = {
                "info": "palette(light)",
                "success": "#6c6",
                "error": "#c66",
            }
            color = colors.get(status, "palette(light)")
            self._status_label.setStyleSheet(
                f"font-size: 11px; color: {color}; background: transparent;"
            )
            self._status_label.setText(text)
            self._status_label.setVisible(True)
        else:
            self._status_label.setStyleSheet(
                "font-size: 11px; color: palette(light); background: transparent;"
            )
            self._status_label.setText(self._default_status_text)
            self._status_label.setVisible(bool(self._default_status_text))

    def _hotkey_event_filter(self, obj, event):
        """Handle right-click on the indicator to toggle this hotkey."""
        if not hasattr(self, "_indicator"):
            return False
        if obj is self._indicator and event.type() == QtCore.QEvent.MouseButtonPress:
            if event.button() == QtCore.Qt.RightButton:
                entry = hotkeys.get_entry(self._action_id) if self._action_id else None
                if entry:
                    entry.set_enabled(not entry.enabled)
                    self._indicator.set_enabled(entry.enabled)
                return True
        return False

    def _update_hotkey_label(self):
        """Update the hotkey label and indicator from the registry."""
        entry = hotkeys.get_entry(self._action_id) if self._action_id else None
        if entry and entry.current_key:
            self._hotkey_label.setText(entry.current_key)
            self._hotkey_label.setVisible(True)
            self._indicator.set_enabled(entry.enabled)
            self._indicator.setVisible(True)
        else:
            self._hotkey_label.setVisible(False)
            self._indicator.setVisible(False)

    def refresh_hotkey(self):
        """Refresh the hotkey display and indicator state."""
        self._update_hotkey_label()
        if self._action_id:
            entry = hotkeys.get_entry(self._action_id)
            if entry:
                effectively_on = entry.enabled and hotkeys.are_all_enabled()
                self._indicator.set_enabled(effectively_on)


class HotkeyToolGroup(_HotkeyHeaderMixin, QtWidgets.QWidget):
    """Non-collapsible tool group with hotkey display.

    Layout:
        [Title (bold)              Alt+Ctrl+W  [■]]
        [description (dim)]
        [content area]
    """

    def __init__(self, title="", description="", action_id=None, parent=None):
        super().__init__(parent)
        self._action_id = action_id

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # -- Header --
        header = QtWidgets.QWidget()
        header.setStyleSheet("background: palette(mid);")
        header_main_layout = QtWidgets.QVBoxLayout(header)
        header_main_layout.setContentsMargins(8, 4, 8, 4)
        header_main_layout.setSpacing(2)

        # Top row: title, hotkey, indicator
        top_row = QtWidgets.QHBoxLayout()
        top_row.setSpacing(8)

        title_label = QtWidgets.QLabel(title)
        title_label.setStyleSheet("font-weight: bold; background: transparent;")
        top_row.addWidget(title_label)
        top_row.addStretch()

        self._build_hotkey_header_widgets(top_row)
        header_main_layout.addLayout(top_row)

        # Status/description line
        self._build_status_label(header_main_layout, default_text=description)

        main_layout.addWidget(header)

        from mkitten.ui.base_tab import make_draggable
        make_draggable(self, header)

        # -- Content area --
        self._content = QtWidgets.QWidget()
        self._content.setObjectName("hotkeyToolGroupContent")
        self._content.setStyleSheet(
            "#hotkeyToolGroupContent { background: rgba(0, 0, 0, 30); }"
        )
        self._content_layout = QtWidgets.QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(8, 4, 4, 4)
        self._content_layout.setSpacing(4)
        main_layout.addWidget(self._content)

    def eventFilter(self, obj, event):
        return self._hotkey_event_filter(obj, event)

    def add_widget(self, widget):
        self._content_layout.addWidget(widget)

    def add_layout(self, layout):
        self._content_layout.addLayout(layout)


class CollapsibleHotkeyToolGroup(_HotkeyHeaderMixin, QtWidgets.QWidget):
    """Collapsible tool group with hotkey display.

    Layout:
        [▼ Title (bold)            Alt+Ctrl+W  [■]]
        [description (dim)]
        [content area - collapsible]

    Click the header to expand/collapse. Right-click indicator
    to toggle the hotkey.
    """

    collapsed_changed = QtCore.Signal(bool)

    def __init__(self, title="", description="", action_id=None,
                 collapsed=False, parent=None):
        super().__init__(parent)
        self._action_id = action_id
        self._title = title
        self._collapsed = collapsed

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # -- Header (clickable) --
        self._header = QtWidgets.QWidget()
        self._header.setStyleSheet("background: palette(mid);")
        self._header.setCursor(QtCore.Qt.PointingHandCursor)
        self._header.installEventFilter(self)

        header_main_layout = QtWidgets.QVBoxLayout(self._header)
        header_main_layout.setContentsMargins(8, 4, 8, 4)
        header_main_layout.setSpacing(2)

        # Top row: arrow + title, hotkey, indicator
        top_row = QtWidgets.QHBoxLayout()
        top_row.setSpacing(8)

        self._title_label = QtWidgets.QLabel()
        self._title_label.setStyleSheet(
            "font-weight: bold; background: transparent;"
        )
        self._update_title_text()
        top_row.addWidget(self._title_label)
        top_row.addStretch()

        self._build_hotkey_header_widgets(top_row)
        header_main_layout.addLayout(top_row)

        # Status/description line
        self._build_status_label(header_main_layout, default_text=description)

        main_layout.addWidget(self._header)

        from mkitten.ui.base_tab import make_draggable
        make_draggable(self, self._header)

        # -- Content area --
        self._content = QtWidgets.QWidget()
        self._content.setObjectName("collapsibleHotkeyContent")
        self._content.setStyleSheet(
            "#collapsibleHotkeyContent { background: rgba(0, 0, 0, 30); }"
        )
        self._content_layout = QtWidgets.QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(8, 4, 4, 4)
        self._content_layout.setSpacing(4)
        self._content.setVisible(not collapsed)
        main_layout.addWidget(self._content)

    def eventFilter(self, obj, event):
        # Header click to toggle collapse
        if obj is self._header and event.type() == QtCore.QEvent.MouseButtonPress:
            if event.button() == QtCore.Qt.LeftButton:
                self.set_collapsed(not self._collapsed)
                return True

        # Indicator right-click
        result = self._hotkey_event_filter(obj, event)
        if result:
            return True

        return False

    def is_collapsed(self):
        return self._collapsed

    def set_collapsed(self, collapsed):
        self._collapsed = collapsed
        self._content.setVisible(not collapsed)
        self._update_title_text()
        self.collapsed_changed.emit(collapsed)

    def _update_title_text(self):
        arrow = "\u25B6" if self._collapsed else "\u25BC"
        self._title_label.setText(f"{arrow}  {self._title}")

    def add_widget(self, widget):
        self._content_layout.addWidget(widget)

    def add_layout(self, layout):
        self._content_layout.addLayout(layout)
