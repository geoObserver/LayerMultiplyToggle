# -----------------------------------------------------------------------------#
# Title:       LayerMultiplyToggle                                             #
# Author:      Mike Elstermann alias mikeE. & #geoObserver                     #
# Version:     v0.4                                                            #
# Created:     21.02.2026                                                      #
# Last Change: 26.05.2026                                                      #
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
        self._ctx_connected = False
        self._cleared_connected = False
        # layer id -> blend mode (int) captured when multiply was switched on
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
        project = QgsProject.instance()
        project.readProject.connect(self._restore_state)
        # cleared was added in QGIS 3.2; guard so we still load on 3.0/3.1.
        if hasattr(project, "cleared"):
            project.cleared.connect(self._restore_state)
            self._cleared_connected = True
        self._restore_state()

        # Append entries to the layer-tree context menu (QGIS >= 3.32 only).
        view = self.iface.layerTreeView()
        if hasattr(view, "contextMenuAboutToShow"):
            view.contextMenuAboutToShow.connect(self._extend_context_menu)
            self._ctx_connected = True
        else:
            self._log("Layer-tree context menu needs QGIS >= 3.32; skipped.",
                      Qgis.Warning)

        self._log("Multiply action ready in toolbar 'geoObserverTools'.")

    def unload(self):
        """Remove the plugin GUI on unload."""
        project = QgsProject.instance()
        try:
            project.readProject.disconnect(self._restore_state)
        except (TypeError, RuntimeError):
            pass
        if self._cleared_connected:
            try:
                project.cleared.disconnect(self._restore_state)
            except (TypeError, RuntimeError):
                pass
            self._cleared_connected = False

        if self._ctx_connected:
            try:
                self.iface.layerTreeView().contextMenuAboutToShow.disconnect(
                    self._extend_context_menu
                )
            except (TypeError, RuntimeError):
                pass
            self._ctx_connected = False

        # Detach our action from the toolbar so the empty-check below is valid.
        if self.toolbar is not None and self.action is not None:
            self.toolbar.removeAction(self.action)
        if self.action is not None:
            # The action is parented to the main window, so removeAction does
            # not free it; delete it explicitly so reloads do not accumulate.
            self.action.deleteLater()
        self.action = None

        # Only remove toolbar if it is empty after removing our action
        if self.toolbar is not None:
            if len(self.toolbar.actions()) == 0:
                # Plugin Reloader calls unload() then initGui() in the same
                # event-loop tick. deleteLater() is deferred, so clear the
                # objectName first: otherwise the immediate initGui() findChild()
                # would re-attach to this dying toolbar and lose our button.
                self.toolbar.setObjectName("")
                self.iface.mainWindow().removeToolBar(self.toolbar)
                self.toolbar.deleteLater()
            self.toolbar = None

    def _multiply_mode(self):
        """Return the Multiply CompositionMode (Qt5/Qt6 compatible)."""
        try:
            return QPainter.CompositionMode.CompositionMode_Multiply  # Qt6
        except AttributeError:
            return QPainter.CompositionMode_Multiply  # Qt5

    def _mode_to_int(self, mode):
        """Serialize a QPainter CompositionMode to int (Qt5/Qt6 safe)."""
        try:
            return int(mode)
        except (TypeError, ValueError):
            return int(getattr(mode, "value", 0))

    def _mode_from_int(self, value):
        """Convert a stored integer back into a QPainter CompositionMode.

        Returns None for an invalid stored value so callers can skip the layer
        instead of silently forcing a wrong (Multiply) blend mode onto it.
        """
        try:
            return QPainter.CompositionMode(int(value))
        except (ValueError, TypeError):
            return None

    def set_blend_mode(self, node, mode):
        """Recursively set blend mode for all layers and groups."""
        if isinstance(node, QgsLayerTreeGroup):
            # Groups carry no own paint-time blend mode here; only the
            # descendant layers produce the visible effect.
            for child in node.children():
                self.set_blend_mode(child, mode)
        elif isinstance(node, QgsLayerTreeLayer):
            layer = node.layer()
            if layer:
                self._apply_to_layer(layer, mode)

    def _apply_to_layer(self, layer, mode):
        """Set a layer's blend mode, capturing its original once for restore.

        The original is stored as int (keyed by layer id) so it can be
        persisted to the project and restored later.
        """
        if layer.id() not in self.saved_blend_modes:
            self.saved_blend_modes[layer.id()] = self._mode_to_int(layer.blendMode())
        layer.setBlendMode(mode)
        layer.triggerRepaint()

    def restore_blend_modes(self):
        """Restore the blend modes captured when multiply was activated."""
        project = QgsProject.instance()
        for layer_id, original_mode in self.saved_blend_modes.items():
            layer = project.mapLayer(layer_id)
            if not layer:
                continue
            mode = self._mode_from_int(original_mode)
            if mode is None:
                self._log(
                    f"Skipped restore of layer {layer_id}: invalid stored blend "
                    f"mode {original_mode!r}.", Qgis.Warning
                )
                continue
            layer.setBlendMode(mode)
            layer.triggerRepaint()
        self.saved_blend_modes.clear()

    def _save_state(self):
        """Persist the active flag and captured blend modes into the project.

        Writes only when something actually changed: writeEntry marks the
        project dirty, so skipping no-op writes avoids spurious "unsaved
        changes" prompts. A real state change still dirties the project,
        which is required to persist.
        """
        project = QgsProject.instance()
        active = bool(self.action is not None and self.action.isChecked())
        modes_json = json.dumps(self.saved_blend_modes)

        cur_active, _ = project.readBoolEntry(LOG_TAG, "active", False)
        cur_modes, _ = project.readEntry(LOG_TAG, "saved_modes", "")
        if cur_active == active and cur_modes == modes_json:
            return

        project.writeEntry(LOG_TAG, "active", active)
        project.writeEntry(LOG_TAG, "saved_modes", modes_json)

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
                parsed = json.loads(raw)
                # Guard against a non-object JSON (e.g. "null"/"[...]") whose
                # .items() would raise AttributeError in this readProject slot.
                if isinstance(parsed, dict):
                    modes = {str(k): int(v) for k, v in parsed.items()}
            except (ValueError, TypeError):
                modes = {}
        self.saved_blend_modes = modes
        self._reflect_state(active)

    def _node_layer_ids(self, nodes):
        """Collect deduplicated layer ids under the given nodes (recursive).

        Deduplication (order preserving) avoids double work and inflated counts
        when a group and one of its child layers are selected together.
        """
        ids = []
        seen = set()

        def walk(node):
            if isinstance(node, QgsLayerTreeGroup):
                for child in node.children():
                    walk(child)
            elif isinstance(node, QgsLayerTreeLayer):
                layer = node.layer()
                if layer and layer.id() not in seen:
                    seen.add(layer.id())
                    ids.append(layer.id())

        for node in nodes:
            walk(node)
        return ids

    def _extend_context_menu(self, menu):
        """Append apply/restore entries to the layer-tree context menu."""
        nodes = self.iface.layerTreeView().selectedNodes()
        if not nodes:
            return
        # Resolve to layer ids now so the slots do not hold layer-tree node
        # pointers that may be invalidated before the menu action is triggered.
        layer_ids = self._node_layer_ids(nodes)
        if not layer_ids:
            return

        menu.addSeparator()
        sub = menu.addMenu("Layer Multiply Toggle")
        apply_act = sub.addAction("Apply multiply")
        apply_act.triggered.connect(
            lambda checked=False, ids=layer_ids: self._ctx_apply(ids)
        )
        restore_act = sub.addAction("Restore original blend mode")
        restore_act.setEnabled(any(i in self.saved_blend_modes for i in layer_ids))
        restore_act.triggered.connect(
            lambda checked=False, ids=layer_ids: self._ctx_restore(ids)
        )

    def _ctx_apply(self, layer_ids):
        """Apply multiply to the given layers (from the context menu)."""
        mode = self._multiply_mode()
        project = QgsProject.instance()
        count = 0
        for layer_id in layer_ids:
            layer = project.mapLayer(layer_id)
            if layer:
                self._apply_to_layer(layer, mode)
                count += 1
        # Invariant: the toggle is "on" iff we currently hold saved layers.
        self._reflect_state(bool(self.saved_blend_modes))
        self._save_state()
        self.iface.mapCanvas().refresh()
        self._notify(f"Multiply applied to {count} layer(s).")

    def _ctx_restore(self, layer_ids):
        """Restore the original blend mode for the given layers (context menu)."""
        project = QgsProject.instance()
        count = 0
        for layer_id in layer_ids:
            if layer_id not in self.saved_blend_modes:
                continue
            mode = self._mode_from_int(self.saved_blend_modes[layer_id])
            layer = project.mapLayer(layer_id)
            if mode is None:
                self._log(
                    f"Skipped restore of layer {layer_id}: invalid stored blend mode.",
                    Qgis.Warning,
                )
            elif layer:
                layer.setBlendMode(mode)
                layer.triggerRepaint()
                count += 1
            del self.saved_blend_modes[layer_id]
        # Invariant: if nothing is left applied, the toggle must read "off".
        self._reflect_state(bool(self.saved_blend_modes))
        self._save_state()
        self.iface.mapCanvas().refresh()
        self._notify(f"Original blend mode restored for {count} layer(s).")

    def _apply_multiply(self):
        """Apply multiply to the selected nodes, or the whole tree if none.

        Originals are captured per layer on first write, so this can be called
        repeatedly to extend coverage without losing the initial state.
        Returns a human-readable description of the affected scope.
        """
        root = QgsProject.instance().layerTreeRoot()
        mode = self._multiply_mode()

        # Selected layers/groups take precedence; otherwise the whole tree.
        selected_nodes = self.iface.layerTreeView().selectedNodes()
        target_nodes = selected_nodes if selected_nodes else root.children()
        for node in target_nodes:
            self.set_blend_mode(node, mode)

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
