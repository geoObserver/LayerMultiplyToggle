# -----------------------------------------------------------------------------#
# Title:       LayerMultiplyToggle                                             #
# Author:      Mike Elstermann alias mikeE. & #geoObserver                     #
# Version:     v0.2                                                            #
# Created:     21.02.2026                                                      #
# Last Change: 24.02.2026                                                      #
# see also:    https://geoobserver.de/qgis-plugins/                            #
#                                                                              #
# This file contains code generated with assistance from an AI (Claude.ai)     #
# No warranty is provided for AI-generated portions.                           #
# Human review and modification performed by: Mike Elstermann (#geoObserver)   #
# -----------------------------------------------------------------------------#

import json
import os
from qgis.PyQt.QtGui import QPainter, QIcon
from qgis.PyQt.QtWidgets import QToolBar
try:
    from qgis.PyQt.QtWidgets import QAction  # Qt5 / QGIS 3.x
except ImportError:
    from qgis.PyQt.QtGui import QAction  # Qt6 / QGIS 4.x
from qgis.core import (
    Qgis,
    QgsProject,
    QgsLayerTreeGroup,
    QgsLayerTreeLayer,
    QgsMessageLog,
)

LOG_TAG = "LayerMultiplyToggle"


class LayerMultiplyToggle:

    def __init__(self, iface):
        self.iface = iface
        self.toolbar = None
        self.action = None
        # layer id -> blend mode captured when multiply was switched on
        self.saved_blend_modes = {}
        self.plugin_dir = os.path.dirname(__file__)

        # Icon paths (bundled with plugin)
        self.ICON_OFF = os.path.join(self.plugin_dir, "icons", "multiply_layers_icon_noactive.png")
        self.ICON_ON = os.path.join(self.plugin_dir, "icons", "multiply_layers_icon_active.png")

    def _log(self, message, level=Qgis.Info):
        """Write a line to the QGIS message log under the plugin's tag."""
        QgsMessageLog.logMessage(message, LOG_TAG, level)

    def _notify(self, message, level=Qgis.Info):
        """Show a transient message in the QGIS message bar and log it."""
        self.iface.messageBar().pushMessage(
            "Layer Multiply Toggle", message, level=level, duration=3
        )
        self._log(message, level)

    def initGui(self):
        """Initialize the plugin GUI."""

        # Find or create toolbar
        self.toolbar = self.iface.mainWindow().findChild(QToolBar, "geoObserverTools")
        if self.toolbar is None:
            self.toolbar = QToolBar("geoObserverTools")
            self.toolbar.setObjectName("geoObserverTools")
            self.iface.mainWindow().addToolBar(self.toolbar)
            self._log("Toolbar 'geoObserverTools' created.")
        else:
            self._log("Toolbar 'geoObserverTools' found.")

        # Create a checkable action; QToolBar renders it as a themed
        # QToolButton that honours the QGIS icon size and dark/light theme.
        self.action = QAction(QIcon(self.ICON_OFF), "Multiply blend mode",
                              self.iface.mainWindow())
        self.action.setCheckable(True)
        self.action.setToolTip("Multiply mode: OFF – click to activate")
        self.action.toggled.connect(self.toggle_multiply)

        self.toolbar.addAction(self.action)

        # Keep the action in sync with the active project's persisted state.
        QgsProject.instance().readProject.connect(self._restore_state)
        QgsProject.instance().cleared.connect(self._restore_state)
        self._restore_state()

        self._log("Multiply action ready in toolbar 'geoObserverTools'.")

    def unload(self):
        """Remove the plugin GUI on unload."""
        try:
            QgsProject.instance().readProject.disconnect(self._restore_state)
            QgsProject.instance().cleared.disconnect(self._restore_state)
        except (TypeError, RuntimeError):
            pass

        # Detach our action from the toolbar so the empty-check below is valid.
        if self.toolbar is not None and self.action is not None:
            self.toolbar.removeAction(self.action)
        self.action = None

        # Only remove toolbar if it is empty after removing our action
        if self.toolbar is not None:
            if len(self.toolbar.actions()) == 0:
                self.iface.mainWindow().removeToolBar(self.toolbar)
                self.toolbar.deleteLater()
            self.toolbar = None

    def _multiply_mode(self):
        """Return the Multiply CompositionMode (Qt5/Qt6 compatible)."""
        try:
            return QPainter.CompositionMode.CompositionMode_Multiply  # Qt6
        except AttributeError:
            return QPainter.CompositionMode_Multiply  # Qt5

    def _mode_from_int(self, value):
        """Convert a stored integer back into a QPainter CompositionMode."""
        try:
            return QPainter.CompositionMode(int(value))
        except (ValueError, TypeError):
            return self._multiply_mode()

    def set_blend_mode(self, node, mode):
        """Recursively set blend mode for all layers and groups."""
        if isinstance(node, QgsLayerTreeGroup):
            # Groups carry no own paint-time blend mode here; only the
            # descendant layers produce the visible effect. The previous
            # setCustomProperty("rendering/blendMode", ...) stored a
            # QPainter enum that QGIS never applied or repainted.
            for child in node.children():
                self.set_blend_mode(child, mode)
        elif isinstance(node, QgsLayerTreeLayer):
            layer = node.layer()
            if layer:
                # Remember the original mode once (stored as int so it can be
                # persisted to the project) so toggling off can restore it.
                if layer.id() not in self.saved_blend_modes:
                    self.saved_blend_modes[layer.id()] = int(layer.blendMode())
                layer.setBlendMode(mode)
                layer.triggerRepaint()

    def restore_blend_modes(self):
        """Restore the blend modes captured when multiply was activated."""
        project = QgsProject.instance()
        for layer_id, original_mode in self.saved_blend_modes.items():
            layer = project.mapLayer(layer_id)
            if layer:
                layer.setBlendMode(self._mode_from_int(original_mode))
                layer.triggerRepaint()
        self.saved_blend_modes.clear()

    def _save_state(self):
        """Persist the active flag and captured blend modes into the project."""
        project = QgsProject.instance()
        active = bool(self.action is not None and self.action.isChecked())
        project.writeEntry(LOG_TAG, "active", active)
        project.writeEntry(LOG_TAG, "saved_modes", json.dumps(self.saved_blend_modes))

    def _reflect_state(self, active):
        """Mirror the active flag in the action without re-applying anything."""
        if self.action is None:
            return
        self.action.blockSignals(True)
        self.action.setChecked(active)
        if active:
            self.action.setIcon(QIcon(self.ICON_ON))
            self.action.setToolTip("Multiply mode: ON – click to deactivate")
        else:
            self.action.setIcon(QIcon(self.ICON_OFF))
            self.action.setToolTip("Multiply mode: OFF – click to activate")
        self.action.blockSignals(False)

    def _restore_state(self, *args):
        """Load persisted state from the current project and mirror it.

        The layers already carry their stored blend mode from the project file,
        so we only reload the captured originals and reflect the on/off state;
        we never re-apply multiply here (that would corrupt the saved originals).
        """
        project = QgsProject.instance()
        active, _ = project.readBoolEntry(LOG_TAG, "active", False)
        raw, _ = project.readEntry(LOG_TAG, "saved_modes", "")
        modes = {}
        if raw:
            try:
                modes = {str(k): int(v) for k, v in json.loads(raw).items()}
            except (ValueError, TypeError):
                modes = {}
        self.saved_blend_modes = modes
        self._reflect_state(active)

    def _apply_multiply(self):
        """Apply multiply to the selected nodes, or the whole tree if none.

        Originals are captured per layer on first write, so this can be called
        repeatedly to extend coverage without losing the initial state.
        Returns a human-readable description of the affected scope.
        """
        root = QgsProject.instance().layerTreeRoot()
        multiply_mode = self._multiply_mode()

        # Selected layers/groups take precedence; otherwise the whole tree.
        selected_nodes = self.iface.layerTreeView().selectedNodes()
        target_nodes = selected_nodes if selected_nodes else root.children()
        for node in target_nodes:
            self.set_blend_mode(node, multiply_mode)

        if selected_nodes:
            return f"{len(selected_nodes)} selected layer(s)/group(s)"
        return "all layers"

    def toggle_multiply(self, checked):
        """Global on/off switch: multiply is a project-wide state.

        On enable it is applied to the current selection (or the whole tree if
        nothing is selected); on disable every layer it touched is restored.
        The on/off state is intentionally decoupled from the current selection.
        """
        if checked:
            self.action.setIcon(QIcon(self.ICON_ON))
            self.action.setToolTip("Multiply mode: ON – click to deactivate")
            self._notify(f"Multiply applied to {self._apply_multiply()}.")
        else:
            self.action.setIcon(QIcon(self.ICON_OFF))
            self.action.setToolTip("Multiply mode: OFF – click to activate")
            self.restore_blend_modes()
            self._notify("Original blend modes restored.")

        self._save_state()
        self.iface.mapCanvas().refresh()
