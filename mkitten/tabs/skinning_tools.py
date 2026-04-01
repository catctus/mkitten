"""Skinning Tools tab."""

from PySide6 import QtWidgets, QtCore

from mkitten import hotkeys
from mkitten.ui.base_tab import BaseTab
from mkitten.utils import skin, selection
from mkitten.widgets.hotkey_tool_group import CollapsibleHotkeyToolGroup
from mkitten.widgets.viewport_slider import ViewportSlider


class AverageWeightsTool(CollapsibleHotkeyToolGroup):
    """Interactive tool for averaging skin weights on selected vertices."""

    ACTION_ID = "average_weights"
    DEFAULT_KEY = "Alt+Ctrl+W"

    def __init__(self, parent=None):
        super().__init__(
            "Average Weights",
            "Smooth weights on selection",
            action_id=self.ACTION_ID,
            collapsed=True,
            parent=parent,
        )

        # -- Capture selection button --
        self._capture_btn = QtWidgets.QPushButton("Capture Selection")
        self._capture_btn.clicked.connect(self._capture_selection)
        self.add_widget(self._capture_btn)

        # -- Blend slider --
        slider_layout = QtWidgets.QHBoxLayout()
        slider_layout.setSpacing(8)

        slider_label = QtWidgets.QLabel("Blend:")
        slider_layout.addWidget(slider_label)

        self._slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self._slider.setRange(0, 100)
        self._slider.setValue(0)
        self._slider.setTracking(True)
        self._slider.valueChanged.connect(self._on_slider_changed)
        self._slider.sliderReleased.connect(self._on_slider_released)
        slider_layout.addWidget(self._slider)

        self._slider_value_label = QtWidgets.QLabel("0%")
        self._slider_value_label.setMinimumWidth(35)
        slider_layout.addWidget(self._slider_value_label)

        self.add_layout(slider_layout)

        # -- Internal state --
        self._mesh = None
        self._skin_cluster = None
        self._falloff = {}
        self._original_weights = {}
        self._average_weights = {}
        self._viewport_slider = None

        # Register hotkey — fires capture with viewport slider
        hotkeys.register(
            self.ACTION_ID,
            "Average Weights - Capture Selection",
            self.DEFAULT_KEY,
            self._hotkey_capture,
            group="Skinning",
        )
        self.refresh_hotkey()

    # -- Core logic (shared) ------------------------------------------------

    def _do_capture(self):
        """Capture selection and compute average. Returns True on success."""
        # Apply previous blend if we had one in progress
        if self._original_weights and self._average_weights and self._slider.value() > 0:
            blended = self._blend_weights(self._slider.value() / 100.0)
            skin.set_vertex_weights(self._skin_cluster, blended)

        mesh, falloff = selection.get_vertices_with_falloff()
        if not mesh or not falloff:
            self.set_status("No vertices selected", "error")
            self._reset_state()
            return False

        skin_cluster = skin.get_skin_cluster(mesh)
        if not skin_cluster:
            self.set_status("No skin cluster found", "error")
            self._reset_state()
            return False

        self._mesh = mesh
        self._skin_cluster = skin_cluster
        self._falloff = falloff

        vertex_indices = list(falloff.keys())
        self._original_weights = skin.get_vertex_weights(skin_cluster, vertex_indices)

        self._average_weights = self._compute_average(
            self._original_weights, self._falloff
        )

        vert_count = len(vertex_indices)
        inf_count = len(self._average_weights)
        self.set_status(
            f"{vert_count} vertices captured ({inf_count} influences)", "success"
        )
        return True

    def _apply_blend(self, blend):
        """Apply a blend value to the weights."""
        if not self._original_weights or not self._average_weights:
            return
        blended = self._blend_weights(blend)
        skin.set_vertex_weights(self._skin_cluster, blended)

    # -- UI button callback -------------------------------------------------

    def _capture_selection(self):
        """Called from the UI button — capture and apply at 100%."""
        if not self._do_capture():
            return

        self._apply_blend(1.0)
        self._slider.blockSignals(True)
        self._slider.setValue(100)
        self._slider.blockSignals(False)
        self._slider_value_label.setText("100%")

    # -- Hotkey callback (viewport slider) ----------------------------------

    def _hotkey_capture(self):
        """Called from hotkey — capture and show viewport slider."""
        if not self._do_capture():
            return

        # Apply at 100% initially
        self._apply_blend(1.0)
        self._slider.blockSignals(True)
        self._slider.setValue(100)
        self._slider.blockSignals(False)
        self._slider_value_label.setText("100%")

        # Show viewport slider
        self._viewport_slider = ViewportSlider(
            label="Blend", min_val=0.0, max_val=1.0, default=1.0
        )
        self._viewport_slider.value_changed.connect(self._on_viewport_slider_changed)
        self._viewport_slider.applied.connect(self._on_viewport_slider_applied)
        self._viewport_slider.cancelled.connect(self._on_viewport_slider_cancelled)
        self._viewport_slider.show_at_cursor()

    def _on_viewport_slider_changed(self, value):
        """Viewport slider moved — update weights and sync UI slider."""
        self._apply_blend(value)
        self._slider.blockSignals(True)
        self._slider.setValue(int(value * 100))
        self._slider.blockSignals(False)
        self._slider_value_label.setText(f"{int(value * 100)}%")

    def _on_viewport_slider_applied(self, value):
        """Viewport slider applied — bake current weights."""
        self._apply_blend(value)
        self._slider.blockSignals(True)
        self._slider.setValue(int(value * 100))
        self._slider.blockSignals(False)
        self._slider_value_label.setText(f"{int(value * 100)}%")
        self.set_status(f"Applied at {int(value * 100)}%", "success")
        self._viewport_slider = None

    def _on_viewport_slider_cancelled(self):
        """Viewport slider cancelled — revert to original weights."""
        if self._original_weights:
            skin.set_vertex_weights(self._skin_cluster, self._original_weights)
        self._slider.blockSignals(True)
        self._slider.setValue(0)
        self._slider.blockSignals(False)
        self._slider_value_label.setText("0%")
        self.set_status("Cancelled", "info")
        self._viewport_slider = None

    # -- Shared helpers -----------------------------------------------------

    def _compute_average(self, vertex_weights, falloff):
        accumulator = {}
        total_falloff = 0.0

        for vi, inf_weights in vertex_weights.items():
            f = falloff.get(vi, 1.0)
            total_falloff += f
            for inf_idx, w in inf_weights.items():
                accumulator[inf_idx] = accumulator.get(inf_idx, 0.0) + w * f

        if total_falloff <= 0.0:
            return {}

        for inf_idx in accumulator:
            accumulator[inf_idx] /= total_falloff

        return accumulator

    def _on_slider_changed(self, value):
        if not self._original_weights or not self._average_weights:
            return

        blend = value / 100.0
        self._slider_value_label.setText(f"{value}%")

        blended = self._blend_weights(blend)
        skin.set_vertex_weights(self._skin_cluster, blended)

    def _on_slider_released(self):
        if self._slider.value() == 0 and self._original_weights:
            skin.set_vertex_weights(self._skin_cluster, self._original_weights)

    def _blend_weights(self, blend):
        result = {}

        for vi, orig in self._original_weights.items():
            falloff = self._falloff.get(vi, 1.0)
            effective_blend = blend * falloff

            blended = {}
            all_influences = set(orig.keys()) | set(self._average_weights.keys())

            for inf_idx in all_influences:
                orig_w = orig.get(inf_idx, 0.0)
                avg_w = self._average_weights.get(inf_idx, 0.0)
                blended[inf_idx] = orig_w + (avg_w - orig_w) * effective_blend

            result[vi] = blended

        return result

    def _reset_state(self):
        self._mesh = None
        self._skin_cluster = None
        self._falloff = {}
        self._original_weights = {}
        self._average_weights = {}


class SkinningToolsTab(BaseTab):

    TAB_NAME = "Skinning"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.add_tool_widget(AverageWeightsTool(), tool_id="average_weights")
        self.restore_layout()
