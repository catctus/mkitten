"""Hotkey manager - Qt-based shortcuts that live only while the UI is open.

Uses an application-level event filter to intercept key events before
Maya's own hotkey system can consume them. Shortcuts are active while
the tool window exists and enabled, and are fully removed when the
window closes. No Maya hotkeys are permanently modified.
"""

from PySide6 import QtWidgets, QtGui, QtCore
from mkitten import prefs


# Default hotkey bindings: {action_id: key_sequence_string}
DEFAULT_BINDINGS = {}

# Global registry of all hotkey entries
_registry = {}
_parent_widget = None
_all_enabled = True
_event_filter = None


class _HotkeyEventFilter(QtCore.QObject):
    """Application-level event filter that intercepts key events."""

    def eventFilter(self, obj, event):
        if not _all_enabled:
            return False

        if event.type() != QtCore.QEvent.KeyPress:
            return False

        key = event.key()
        # Ignore bare modifier presses
        if key in (
            QtCore.Qt.Key_Control, QtCore.Qt.Key_Shift,
            QtCore.Qt.Key_Alt, QtCore.Qt.Key_Meta,
        ):
            return False

        modifiers = event.modifiers()
        pressed = QtGui.QKeySequence(modifiers.value | key)

        for entry in _registry.values():
            if not entry.enabled or not entry.current_key:
                continue
            bound = QtGui.QKeySequence(entry.current_key)
            if pressed.matches(bound) == QtGui.QKeySequence.ExactMatch:
                if entry.callback:
                    entry.callback()
                return True  # consume the event

        return False


class HotkeyEntry:
    """A single registered hotkey action."""

    def __init__(self, action_id, label, default_key, callback, group="General"):
        self.action_id = action_id
        self.label = label
        self.default_key = default_key
        self.callback = callback
        self.group = group
        self.enabled = True

        # Load saved binding or use default
        saved = prefs.get("hotkeys", action_id)
        self.current_key = saved if saved is not None else default_key

    def set_enabled(self, enabled):
        """Enable or disable this individual hotkey."""
        self.enabled = enabled

    def set_key(self, key_sequence_string):
        """Change the key binding."""
        self.current_key = key_sequence_string

    def reset_to_default(self):
        """Reset to the default key binding."""
        self.set_key(self.default_key)
        # Remove saved override
        saved = prefs.get("hotkeys") or {}
        if self.action_id in saved:
            del saved[self.action_id]
            data = prefs.load()
            data["hotkeys"] = saved
            prefs.save(data)

    def destroy(self):
        """Clean up."""
        self.callback = None


def init(parent_widget):
    """Initialize the hotkey system with the parent widget (ToolWindow)."""
    global _parent_widget, _all_enabled, _event_filter
    _parent_widget = parent_widget
    _all_enabled = True

    # Install application-level event filter
    app = QtWidgets.QApplication.instance()
    if app:
        _event_filter = _HotkeyEventFilter()
        app.installEventFilter(_event_filter)


def register(action_id, label, default_key, callback, group="General"):
    """Register a hotkey action.

    Args:
        action_id: Unique string ID for this action (e.g. "average_weights").
        label: Human-readable name shown in keybinding UI.
        default_key: Default key sequence string (e.g. "Alt+Ctrl+W").
        callback: Function to call when the hotkey fires.
        group: Group name for organizing in menus (e.g. "Skinning").

    Returns:
        The HotkeyEntry instance.
    """
    DEFAULT_BINDINGS[action_id] = default_key

    # Unregister existing if re-registering (e.g. after reload)
    if action_id in _registry:
        _registry[action_id].destroy()

    entry = HotkeyEntry(action_id, label, default_key, callback, group=group)
    _registry[action_id] = entry
    return entry


def unregister(action_id):
    """Remove a registered hotkey."""
    entry = _registry.pop(action_id, None)
    if entry:
        entry.destroy()


def get_entry(action_id):
    """Get a HotkeyEntry by its action ID."""
    return _registry.get(action_id)


def get_all_entries():
    """Return all registered HotkeyEntry instances."""
    return dict(_registry)


def set_all_enabled(enabled):
    """Enable or disable all hotkeys globally."""
    global _all_enabled
    _all_enabled = enabled


def are_all_enabled():
    """Return whether the global hotkey toggle is on."""
    return _all_enabled


def save_bindings():
    """Save all current bindings to prefs."""
    bindings = {}
    for action_id, entry in _registry.items():
        # Only save if different from default
        if entry.current_key != entry.default_key:
            bindings[action_id] = entry.current_key
    data = prefs.load()
    data["hotkeys"] = bindings
    prefs.save(data)


def shutdown():
    """Destroy all shortcuts. Called when the tool window closes."""
    global _parent_widget, _event_filter

    # Remove event filter
    if _event_filter is not None:
        app = QtWidgets.QApplication.instance()
        if app:
            app.removeEventFilter(_event_filter)
        _event_filter = None

    for entry in _registry.values():
        entry.destroy()
    _registry.clear()
    DEFAULT_BINDINGS.clear()
    _parent_widget = None
