"""Skinning Tools tab."""

from PySide6 import QtWidgets, QtCore

from mkitten import hotkeys
from mkitten.ui.base_tab import BaseTab
from mkitten.utils import skin, selection
from mkitten.widgets.hotkey_tool_group import CollapsibleHotkeyToolGroup


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

        # Register hotkey — fires capture selection
        hotkeys.register(
            self.ACTION_ID,
            "Average Weights - Capture Selection",
            self.DEFAULT_KEY,
            self._capture_selection,
            group="Skinning",
        )
        self.refresh_hotkey()

    def _capture_selection(self):
        """Capture the current selection and compute the average weights."""
        # Apply previous blend if we had one in progress
        if self._original_weights and self._average_weights and self._slider.value() > 0:
            blended = self._blend_weights(self._slider.value() / 100.0)
            skin.set_vertex_weights(self._skin_cluster, blended)

        mesh, falloff = selection.get_vertices_with_falloff()
        if not mesh or not falloff:
            self.set_status("No vertices selected", "error")
            self._reset_state()
            return

        skin_cluster = skin.get_skin_cluster(mesh)
        if not skin_cluster:
            self.set_status("No skin cluster found", "error")
            self._reset_state()
            return

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

        # Apply at full strength and set slider to 100%
        blended = self._blend_weights(1.0)
        skin.set_vertex_weights(self._skin_cluster, blended)
        self._slider.blockSignals(True)
        self._slider.setValue(100)
        self._slider.blockSignals(False)
        self._slider_value_label.setText("100%")

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
