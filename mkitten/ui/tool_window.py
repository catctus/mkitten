"""Main tool window widget that holds the menu bar, top area, tab bar, and tab content."""

from PySide6 import QtWidgets, QtCore, QtGui

from mkitten import hotkeys
from mkitten.tabs import TAB_CLASSES
from mkitten.widgets.hotkey_tool_group import HotkeyToolGroup


class ToolWindow(QtWidgets.QWidget):
    """Top-level widget parented into the Maya workspace control.

    Layout (top to bottom):
        - menu_bar:  Settings, Shortcuts menus
        - top_area:  optional pinned widget provided by the active tab
        - tab_bar:   QTabBar for switching between tabs
        - stack:     QStackedWidget showing the active tab's content
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # Initialize hotkey system with this widget as parent
        hotkeys.init(self)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # -- Menu bar row (menu + hotkey toggle) --
        menu_row = QtWidgets.QHBoxLayout()
        menu_row.setContentsMargins(0, 0, 4, 0)
        menu_row.setSpacing(4)

        self._menu_bar = QtWidgets.QMenuBar()
        self._menu_bar.setNativeMenuBar(False)
        menu_row.addWidget(self._menu_bar)

        self._hotkey_toggle = QtWidgets.QPushButton("Hotkeys: ON")
        self._hotkey_toggle.setCheckable(True)
        self._hotkey_toggle.setChecked(True)
        self._hotkey_toggle.setFixedHeight(20)
        self._hotkey_toggle.setStyleSheet(
            "QPushButton { background: #5a5; padding: 2px 8px; border: none;"
            "  border-radius: 3px; font-size: 11px; }"
            "QPushButton:!checked { background: #a55; }"
        )
        self._hotkey_toggle.toggled.connect(self._on_hotkey_toggle)
        menu_row.addWidget(self._hotkey_toggle)

        main_layout.addLayout(menu_row)

        self._build_menus()

        # -- Top area (swapped per tab) --
        self._top_container = QtWidgets.QWidget()
        self._top_layout = QtWidgets.QVBoxLayout(self._top_container)
        self._top_layout.setContentsMargins(0, 0, 0, 0)
        self._top_layout.setSpacing(0)
        self._top_container.setVisible(False)
        main_layout.addWidget(self._top_container)

        # -- Tab bar --
        self._tab_bar = QtWidgets.QTabBar()
        self._tab_bar.setExpanding(False)
        self._tab_bar.setDrawBase(False)
        main_layout.addWidget(self._tab_bar)

        # -- Stacked content --
        self._stack = QtWidgets.QStackedWidget()
        main_layout.addWidget(self._stack)

        # -- Populate tabs from registry --
        self._tabs = []
        self._top_widgets = []

        for tab_cls in TAB_CLASSES:
            tab_instance = tab_cls(parent=self)
            self._tabs.append(tab_instance)

            self._tab_bar.addTab(tab_instance.TAB_NAME)
            self._stack.addWidget(tab_instance)

            # Cache the top widget (may be None)
            self._top_widgets.append(tab_instance.top_widget())

        # -- Connect tab switching --
        self._tab_bar.currentChanged.connect(self._on_tab_changed)

        # Activate the first tab
        if self._tabs:
            self._on_tab_changed(0)

    def _build_menus(self):
        """Build the menu bar."""
        # -- Settings menu --
        settings_menu = self._menu_bar.addMenu("Settings")

        keybindings_action = settings_menu.addAction("Keybindings...")
        keybindings_action.triggered.connect(self._open_keybindings)

    def _open_keybindings(self):
        from mkitten.ui.keybinding_dialog import KeybindingDialog
        dialog = KeybindingDialog(parent=self)
        dialog.exec()
        self._refresh_hotkey_widgets()

    def _on_hotkey_toggle(self, checked):
        hotkeys.set_all_enabled(checked)
        self._hotkey_toggle.setText("Hotkeys: ON" if checked else "Hotkeys: OFF")
        self._refresh_hotkey_widgets()

    def _refresh_hotkey_widgets(self):
        """Find all HotkeyToolGroup widgets and refresh their labels."""
        for widget in self.findChildren(HotkeyToolGroup):
            widget.refresh_hotkey()

    def _on_tab_changed(self, index):
        """Handle tab bar selection change."""
        # Deactivate previous tab
        prev_index = self._stack.currentIndex()
        if prev_index >= 0 and prev_index != index:
            self._tabs[prev_index].on_deactivated()

        # Switch stacked content
        self._stack.setCurrentIndex(index)

        # Swap top area widget
        while self._top_layout.count():
            item = self._top_layout.takeAt(0)
            if item.widget():
                item.widget().setVisible(False)

        top_widget = self._top_widgets[index] if index < len(self._top_widgets) else None
        if top_widget is not None:
            self._top_layout.addWidget(top_widget)
            top_widget.setVisible(True)
            self._top_container.setVisible(True)
        else:
            self._top_container.setVisible(False)

        # Activate new tab
        self._tabs[index].on_activated()

    def closeEvent(self, event):
        """Clean up hotkeys and viewport sliders when the window closes."""
        from mkitten.widgets.viewport_slider import close_all as close_all_sliders
        close_all_sliders()
        hotkeys.shutdown()
        super().closeEvent(event)
