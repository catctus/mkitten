"""A collapsible group widget with a clickable header and toggle arrow."""

from PySide6 import QtWidgets, QtCore


class CollapsibleGroup(QtWidgets.QWidget):
    """A titled section that can be collapsed/expanded by clicking its header.

    Usage::

        group = CollapsibleGroup("Transform Tools")
        group.add_widget(some_button)
        group.add_widget(some_slider)
    """

    def __init__(self, title="", collapsed=False, parent=None):
        super().__init__(parent)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # -- Header button --
        self._header = QtWidgets.QPushButton()
        self._header.setCheckable(True)
        self._header.setChecked(not collapsed)
        self._header.setStyleSheet(
            "QPushButton {"
            "  text-align: left;"
            "  padding: 6px 8px;"
            "  font-weight: bold;"
            "  border: none;"
            "  background: palette(mid);"
            "}"
            "QPushButton:hover {"
            "  background: palette(midlight);"
            "}"
        )
        self._title = title
        self._update_header_text(not collapsed)
        self._header.toggled.connect(self._on_toggled)
        main_layout.addWidget(self._header)

        # Enable drag-and-drop reordering from the header
        from mkitten.ui.base_tab import make_draggable
        make_draggable(self, self._header)

        # -- Content area --
        self._content = QtWidgets.QWidget()
        self._content.setObjectName("collapsibleGroupContent")
        self._content.setStyleSheet("#collapsibleGroupContent { background: rgba(0, 0, 0, 30); }")
        self._content_layout = QtWidgets.QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(8, 4, 4, 4)
        self._content_layout.setSpacing(4)
        self._content.setVisible(not collapsed)
        main_layout.addWidget(self._content)

    def add_widget(self, widget):
        """Add a widget to the collapsible content area."""
        self._content_layout.addWidget(widget)

    def add_layout(self, layout):
        """Add a sub-layout to the collapsible content area."""
        self._content_layout.addLayout(layout)

    def _on_toggled(self, checked):
        self._content.setVisible(checked)
        self._update_header_text(checked)

    def _update_header_text(self, expanded):
        arrow = "\u25BC" if expanded else "\u25B6"
        self._header.setText(f"  {arrow}  {self._title}")
