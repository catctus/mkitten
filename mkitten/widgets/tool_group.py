"""A non-collapsible group widget with a title and optional description."""

from PySide6 import QtWidgets, QtCore, QtGui


class ToolGroup(QtWidgets.QWidget):
    """A titled group box with a header showing name + info text.

    The header displays the tool name on the left (bold) and an optional
    description/tooltip string on the right (smaller, dimmed).

    Usage::

        group = ToolGroup("Copy Weights", "Select source then target")
        group.add_widget(some_button)
        group.add_widget(some_slider)
    """

    def __init__(self, title="", description="", parent=None):
        super().__init__(parent)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # -- Header --
        header = QtWidgets.QWidget()
        header.setStyleSheet(
            "background: palette(mid);"
            "padding: 4px 8px;"
        )
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(8, 4, 8, 4)
        header_layout.setSpacing(8)

        title_label = QtWidgets.QLabel(title)
        title_label.setStyleSheet("font-weight: bold; background: transparent;")
        header_layout.addWidget(title_label)

        if description:
            desc_label = QtWidgets.QLabel(description)
            desc_label.setStyleSheet(
                "font-size: 11px;"
                "color: palette(light);"
                "background: transparent;"
            )
            desc_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            header_layout.addWidget(desc_label)

        main_layout.addWidget(header)

        # Enable drag-and-drop reordering from the header
        from mkitten.ui.base_tab import make_draggable
        make_draggable(self, header)

        # -- Content area --
        self._content = QtWidgets.QWidget()
        self._content.setObjectName("toolGroupContent")
        self._content.setStyleSheet("#toolGroupContent { background: rgba(0, 0, 0, 30); }")
        self._content_layout = QtWidgets.QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(8, 4, 4, 4)
        self._content_layout.setSpacing(4)
        main_layout.addWidget(self._content)

    def add_widget(self, widget):
        """Add a widget to the content area."""
        self._content_layout.addWidget(widget)

    def add_layout(self, layout):
        """Add a sub-layout to the content area."""
        self._content_layout.addLayout(layout)
