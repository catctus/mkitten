"""Base class for all tool tabs."""

from PySide6 import QtWidgets, QtCore, QtGui


class _DragDropScrollContent(QtWidgets.QWidget):
    """Internal widget that acts as the scroll area content with drop support."""

    def __init__(self, tab=None, parent=None):
        super().__init__(parent)
        self._tab = tab
        self.setAcceptDrops(True)
        self._drop_indicator_index = -1

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-maya-tool-widget"):
            event.acceptProposedAction()

    def _widget_count(self):
        """Return the number of real widgets (excludes the trailing stretch)."""
        layout = self.layout()
        count = 0
        for i in range(layout.count()):
            if layout.itemAt(i).widget() is not None:
                count += 1
        return count

    def _find_drop_index(self, y):
        """Find the widget index to drop at based on mouse Y position."""
        layout = self.layout()
        widget_count = self._widget_count()

        for i in range(layout.count()):
            item = layout.itemAt(i)
            widget = item.widget()
            if widget is None:
                continue
            widget_mid = widget.y() + widget.height() / 2
            if y < widget_mid:
                return i
        return widget_count  # after last widget

    def dragMoveEvent(self, event):
        if not event.mimeData().hasFormat("application/x-maya-tool-widget"):
            return

        layout = self.layout()
        if layout is None:
            return

        new_index = self._find_drop_index(event.position().y())

        if new_index != self._drop_indicator_index:
            self._drop_indicator_index = new_index
            self.update()

        event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self._drop_indicator_index = -1
        self.update()

    def dropEvent(self, event):
        self._drop_indicator_index = -1
        self.update()

        mime = event.mimeData()
        if not mime.hasFormat("application/x-maya-tool-widget"):
            return

        # Find the source widget by its id
        widget_id = int(mime.data("application/x-maya-tool-widget").data())
        layout = self.layout()
        source_widget = None
        source_index = -1

        for i in range(layout.count()):
            item = layout.itemAt(i)
            w = item.widget()
            if w is not None and id(w) == widget_id:
                source_widget = w
                source_index = i
                break

        if source_widget is None:
            return

        target_index = self._find_drop_index(event.position().y())

        # Adjust for removal shifting indices
        if source_index < target_index:
            target_index -= 1

        if source_index != target_index:
            layout.removeWidget(source_widget)
            layout.insertWidget(target_index, source_widget)

            # Notify the tab to save layout
            self._save_layout()

        event.acceptProposedAction()

    def _save_layout(self):
        """Ask the owning BaseTab to save layout."""
        if self._tab is not None:
            self._tab.save_layout()

    def paintEvent(self, event):
        super().paintEvent(event)

        if self._drop_indicator_index < 0:
            return

        layout = self.layout()
        if layout is None:
            return

        # Draw a horizontal line at the drop position
        painter = QtGui.QPainter(self)
        pen = QtGui.QPen(QtGui.QColor(100, 160, 255), 2)
        painter.setPen(pen)

        y = 0
        widget_count = self._widget_count()

        if self._drop_indicator_index < widget_count:
            item = layout.itemAt(self._drop_indicator_index)
            widget = item.widget()
            if widget:
                y = widget.y() - layout.spacing()
        else:
            # After the last widget — find the last real widget
            for i in range(layout.count() - 1, -1, -1):
                w = layout.itemAt(i).widget()
                if w is not None:
                    y = w.y() + w.height() + layout.spacing()
                    break

        margin = layout.contentsMargins().left()
        painter.drawLine(margin, int(y), self.width() - margin, int(y))
        painter.end()


def make_draggable(widget, drag_handle):
    """Install drag support on a group widget, initiated from its header.

    Args:
        widget: The group widget that will be dragged.
        drag_handle: The header widget that initiates the drag (e.g. a QLabel,
            QPushButton, or QWidget used as the header).
    """
    drag_handle.installEventFilter(_DragFilter(widget, drag_handle))


class _DragFilter(QtCore.QObject):
    """Event filter that initiates a drag from a header widget."""

    def __init__(self, source_widget, handle, parent=None):
        super().__init__(parent or handle)
        self._source = source_widget
        self._drag_start_pos = None

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.MouseButtonPress:
            if event.button() == QtCore.Qt.LeftButton:
                self._drag_start_pos = event.position().toPoint()

        elif event.type() == QtCore.QEvent.MouseMove:
            if self._drag_start_pos is not None:
                delta = event.position().toPoint() - self._drag_start_pos
                if delta.manhattanLength() >= QtWidgets.QApplication.startDragDistance():
                    self._start_drag()
                    self._drag_start_pos = None
                    return True

        elif event.type() == QtCore.QEvent.MouseButtonRelease:
            self._drag_start_pos = None

        return False

    def _start_drag(self):
        drag = QtGui.QDrag(self._source)
        mime = QtCore.QMimeData()
        mime.setData(
            "application/x-maya-tool-widget",
            QtCore.QByteArray(str(id(self._source)).encode()),
        )
        drag.setMimeData(mime)

        # Semi-transparent snapshot as drag pixmap
        pixmap = self._source.grab()
        painter = QtGui.QPainter(pixmap)
        painter.fillRect(pixmap.rect(), QtGui.QColor(0, 0, 0, 80))
        painter.end()
        drag.setPixmap(pixmap)

        drag.exec(QtCore.Qt.MoveAction)


class BaseTab(QtWidgets.QWidget):
    """Abstract base class that every tab inherits from.

    Provides a scroll area with drag-and-drop reorderable tool widgets.
    Subclasses add tool widgets via ``add_tool_widget()`` and optionally
    override ``top_widget()`` for content pinned above the tab bar.
    """

    TAB_NAME = "Untitled"

    def __init__(self, parent=None):
        super().__init__(parent)

        # -- Main layout --
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # -- Scroll area --
        self._scroll_area = QtWidgets.QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)

        self._scroll_content = _DragDropScrollContent(tab=self)
        self._scroll_layout = QtWidgets.QVBoxLayout(self._scroll_content)
        self._scroll_layout.setContentsMargins(4, 4, 4, 4)
        self._scroll_layout.setSpacing(4)
        # Add a stretch so widgets stay top-aligned but the content
        # fills the full scroll area height for drop targets.
        self._scroll_layout.addStretch(1)

        self._scroll_area.setWidget(self._scroll_content)
        main_layout.addWidget(self._scroll_area)

    def add_tool_widget(self, widget, tool_id=None):
        """Append a tool widget into the scroll area (before the stretch).

        Args:
            widget: The widget to add.
            tool_id: A unique string identifier for this tool. Used for
                saving/restoring layout order and collapsed state.
        """
        if tool_id:
            widget.setProperty("tool_id", tool_id)

            # Connect collapsed_changed signal if the widget supports it
            signal = getattr(widget, "collapsed_changed", None)
            if signal is not None:
                signal.connect(lambda _: self.save_layout())

        stretch_index = self._scroll_layout.count() - 1
        self._scroll_layout.insertWidget(stretch_index, widget)

    def restore_layout(self):
        """Reorder tool widgets and restore collapsed state from prefs."""
        from mkitten import prefs

        saved_order = prefs.get("layout", self.TAB_NAME)
        saved_state = prefs.get("collapsed", self.TAB_NAME) or {}

        # Build a map of tool_id -> widget
        layout = self._scroll_layout
        widgets_by_id = {}
        for i in range(layout.count()):
            w = layout.itemAt(i).widget()
            if w is not None:
                tid = w.property("tool_id")
                if tid:
                    widgets_by_id[tid] = w

        # Reinsert in saved order (before the stretch)
        if saved_order:
            insert_pos = 0
            for tid in saved_order:
                w = widgets_by_id.pop(tid, None)
                if w is not None:
                    layout.removeWidget(w)
                    layout.insertWidget(insert_pos, w)
                    insert_pos += 1

        # Restore collapsed state
        for tid, collapsed in saved_state.items():
            w = widgets_by_id.get(tid)
            if w is None:
                # May have been reinserted above, re-scan
                for i in range(layout.count()):
                    item_w = layout.itemAt(i).widget()
                    if item_w and item_w.property("tool_id") == tid:
                        w = item_w
                        break
            if w is not None and hasattr(w, "set_collapsed"):
                w.set_collapsed(collapsed)

    def save_layout(self):
        """Save the current tool widget order and collapsed state to prefs."""
        from mkitten import prefs

        layout = self._scroll_layout
        order = []
        collapsed_state = {}
        for i in range(layout.count()):
            w = layout.itemAt(i).widget()
            if w is not None:
                tid = w.property("tool_id")
                if tid:
                    order.append(tid)
                    if hasattr(w, "is_collapsed"):
                        collapsed_state[tid] = w.is_collapsed()

        if order:
            prefs.set("layout", self.TAB_NAME, order)
        if collapsed_state:
            prefs.set("collapsed", self.TAB_NAME, collapsed_state)

    def top_widget(self):
        """Override to return a QWidget shown above the tab bar."""
        return None

    def on_activated(self):
        """Called when this tab becomes visible."""

    def on_deactivated(self):
        """Called when this tab is hidden."""
