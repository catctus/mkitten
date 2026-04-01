"""Entry point for the MKitten dockable window.

Usage (shelf button / hotkey / script editor):
    import mkitten.main
    mkitten.main.show()
"""

import sys
import importlib
import types

import maya.cmds as cmds
import maya.OpenMayaUI as omui
from PySide6 import QtWidgets
from shiboken6 import wrapInstance, isValid

WORKSPACE_CONTROL_NAME = "MKittenWorkspaceControl"
UI_SCRIPT = "import mkitten.main; mkitten.main._restore_ui()"

_tool_window_instance = None


def _reload_modules():
    """Reload all mkitten submodules so code changes are picked up.

    Skips mkitten.main to avoid resetting globals mid-execution.
    """
    to_reload = sorted(
        [
            key for key in sys.modules
            if key.startswith("mkitten") and key != "mkitten.main"
        ],
        key=lambda k: k.count("."),
    )
    for mod_name in to_reload:
        mod = sys.modules.get(mod_name)
        if mod is not None and isinstance(mod, types.ModuleType):
            try:
                importlib.reload(mod)
            except Exception:
                pass


def _cleanup():
    """Safely tear down any existing UI."""
    global _tool_window_instance

    try:
        if _tool_window_instance is not None and isValid(_tool_window_instance):
            _tool_window_instance.setParent(None)
            _tool_window_instance.deleteLater()
    except RuntimeError:
        pass
    _tool_window_instance = None

    try:
        if cmds.workspaceControl(WORKSPACE_CONTROL_NAME, exists=True):
            cmds.deleteUI(WORKSPACE_CONTROL_NAME)
    except RuntimeError:
        pass


def show(reload=True):
    """Show the MKitten window, creating it if needed.

    Args:
        reload: If True, reload all mkitten modules before building
            the UI. Set to False in production to avoid potential crashes.
    """
    _cleanup()

    if reload:
        _reload_modules()

    # uiScript fires immediately on creation — it will call _build_ui for us
    cmds.workspaceControl(
        WORKSPACE_CONTROL_NAME,
        label="MKitten",
        retain=True,
        floating=True,
        initialWidth=340,
        initialHeight=600,
        uiScript=UI_SCRIPT,
    )


def _restore_ui():
    """Called by Maya's uiScript when restoring the workspace control on startup."""
    _build_ui()


def _build_ui():
    """Build the ToolWindow widget and parent it into the workspace control."""
    global _tool_window_instance

    ptr = omui.MQtUtil.findControl(WORKSPACE_CONTROL_NAME)
    if ptr is None:
        return

    # Already built — skip
    if _tool_window_instance is not None and isValid(_tool_window_instance):
        return

    workspace_widget = wrapInstance(int(ptr), QtWidgets.QWidget)

    from mkitten.ui.tool_window import ToolWindow

    _tool_window_instance = ToolWindow(parent=workspace_widget)

    layout = workspace_widget.layout()
    if layout is None:
        layout = QtWidgets.QVBoxLayout(workspace_widget)
        layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(_tool_window_instance)
