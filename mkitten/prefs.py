"""Preferences system for MKitten.

Stores user preferences (layout order, shortcuts, tool settings, etc.)
in the user's Maya prefs directory as JSON.
"""

import json
import os


def _prefs_dir():
    """Return the Maya prefs directory for the current version."""
    # Maya sets MAYA_APP_DIR, fall back to ~/maya
    app_dir = os.environ.get("MAYA_APP_DIR", os.path.join(os.path.expanduser("~"), "maya"))
    # Try to detect the current Maya version
    try:
        import maya.cmds as cmds
        version = cmds.about(version=True)
    except Exception:
        version = "2025"
    return os.path.join(app_dir, version, "prefs")


def _prefs_path():
    """Return the full path to the prefs JSON file."""
    return os.path.join(_prefs_dir(), "mkitten_prefs.json")


def load():
    """Load and return the full prefs dictionary.

    Returns an empty dict if the file doesn't exist or can't be read.
    """
    path = _prefs_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save(data):
    """Save the full prefs dictionary to disk.

    Args:
        data: The complete prefs dictionary to write.
    """
    path = _prefs_path()
    prefs_dir = os.path.dirname(path)
    os.makedirs(prefs_dir, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def get(section, key=None, default=None):
    """Read a value from prefs.

    Args:
        section: Top-level section name (e.g. "layout", "shortcuts").
        key: Optional key within the section. If None, returns the
            entire section dict.
        default: Value to return if section/key is missing.

    Returns:
        The stored value, or *default* if not found.
    """
    data = load()
    section_data = data.get(section)
    if section_data is None:
        return default
    if key is None:
        return section_data
    if isinstance(section_data, dict):
        return section_data.get(key, default)
    return default


def set(section, key, value):
    """Write a value to prefs and save to disk.

    Args:
        section: Top-level section name.
        key: Key within the section.
        value: Value to store (must be JSON-serializable).
    """
    data = load()
    if section not in data:
        data[section] = {}
    data[section][key] = value
    save(data)
