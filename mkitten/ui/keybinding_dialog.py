"""Keybinding dialog - rebind, restore defaults, save/close."""

from PySide6 import QtWidgets, QtCore, QtGui

from mkitten import hotkeys


class _KeyCaptureButton(QtWidgets.QPushButton):
    """Button that captures the next key combo when clicked."""

    key_captured = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__("Click to rebind", parent)
        self._capturing = False
        self.clicked.connect(self._start_capture)

    def _start_capture(self):
        self._capturing = True
        self.setText("Press a key...")
        self.setStyleSheet("background: #664; font-style: italic;")
        self.setFocus()
        self.grabKeyboard()

    def keyPressEvent(self, event):
        if not self._capturing:
            super().keyPressEvent(event)
            return

        key = event.key()

        # Ignore bare modifier presses
        if key in (
            QtCore.Qt.Key_Control, QtCore.Qt.Key_Shift,
            QtCore.Qt.Key_Alt, QtCore.Qt.Key_Meta,
        ):
            return

        modifiers = event.modifiers()
        sequence = QtGui.QKeySequence(modifiers.value | key)
        key_string = sequence.toString()

        self._capturing = False
        self.releaseKeyboard()
        self.setStyleSheet("")
        self.setText("Click to rebind")
        self.key_captured.emit(key_string)

    def focusOutEvent(self, event):
        if self._capturing:
            self._capturing = False
            self.releaseKeyboard()
            self.setStyleSheet("")
            self.setText("Click to rebind")
        super().focusOutEvent(event)


class KeybindingDialog(QtWidgets.QDialog):
    """Dialog for viewing and rebinding all registered hotkeys."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Keybindings")
        self.setMinimumWidth(500)
        self.setMinimumHeight(300)

        layout = QtWidgets.QVBoxLayout(self)

        # -- Scroll area for the bindings --
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)

        scroll_content = QtWidgets.QWidget()
        self._bindings_layout = QtWidgets.QVBoxLayout(scroll_content)
        self._bindings_layout.setSpacing(6)
        self._bindings_layout.setAlignment(QtCore.Qt.AlignTop)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        # -- Bottom buttons --
        bottom_layout = QtWidgets.QHBoxLayout()
        bottom_layout.addStretch()

        restore_all_btn = QtWidgets.QPushButton("Restore All Defaults")
        restore_all_btn.clicked.connect(self._restore_all)
        bottom_layout.addWidget(restore_all_btn)

        save_close_btn = QtWidgets.QPushButton("Save && Close")
        save_close_btn.clicked.connect(self._save_and_close)
        bottom_layout.addWidget(save_close_btn)

        layout.addLayout(bottom_layout)

        # Build rows
        self._rows = {}
        self._build_rows()

    def _build_rows(self):
        entries = hotkeys.get_all_entries()

        for action_id, entry in entries.items():
            row = QtWidgets.QWidget()
            row_layout = QtWidgets.QHBoxLayout(row)
            row_layout.setContentsMargins(4, 2, 4, 2)
            row_layout.setSpacing(8)

            # Tool label
            label = QtWidgets.QLabel(entry.label)
            label.setMinimumWidth(150)
            row_layout.addWidget(label)

            # Current binding display
            binding_label = QtWidgets.QLabel(entry.current_key or "Unbound")
            binding_label.setMinimumWidth(120)
            binding_label.setStyleSheet(
                "background: rgba(0, 0, 0, 40);"
                "padding: 4px 8px;"
                "border-radius: 3px;"
            )
            row_layout.addWidget(binding_label)

            # Capture button
            capture_btn = _KeyCaptureButton()
            capture_btn.key_captured.connect(
                lambda key, aid=action_id: self._on_key_captured(aid, key)
            )
            row_layout.addWidget(capture_btn)

            # Restore default button
            default_btn = QtWidgets.QPushButton("Default")
            default_btn.setToolTip(f"Restore to: {entry.default_key}")
            default_btn.clicked.connect(
                lambda checked=False, aid=action_id: self._restore_default(aid)
            )
            row_layout.addWidget(default_btn)

            self._bindings_layout.addWidget(row)
            self._rows[action_id] = {
                "row": row,
                "binding_label": binding_label,
            }

    def _on_key_captured(self, action_id, key_string):
        """Handle a new key being captured for an action."""
        entry = hotkeys.get_entry(action_id)
        if entry:
            entry.set_key(key_string)
            self._rows[action_id]["binding_label"].setText(key_string)

    def _restore_default(self, action_id):
        """Restore a single action to its default binding."""
        entry = hotkeys.get_entry(action_id)
        if entry:
            entry.reset_to_default()
            self._rows[action_id]["binding_label"].setText(
                entry.current_key or "Unbound"
            )

    def _restore_all(self):
        """Restore all actions to their default bindings."""
        for action_id in list(self._rows.keys()):
            self._restore_default(action_id)

    def _save_and_close(self):
        """Save all bindings and close the dialog."""
        hotkeys.save_bindings()
        self.accept()
