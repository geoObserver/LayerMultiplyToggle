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
from qgis.PyQt.QtCore import Qt, QTimer
from qgis.PyQt.QtGui import QPainter, QIcon
from qgis.PyQt.QtWidgets import QToolBar, QMenu
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
from qgis.gui import QgsLayerTreeViewIndicator

LOG_TAG = "LayerMultiplyToggle"


class LayerMultiplyToggle:

    def __init__(self, iface):
        self.iface = iface
        self.toolbar = None
        self.action = None
        self._cleared_connected = False
        self._model = None
        self._model_connected = False
        # while False (after a reset) no per-layer indicators are shown
        self._indicators_enabled = True
        # layer id -> blend mode (int) captured when multiply was switched on
        self.saved_blend_modes = {}
        # layer id -> QgsLayerTreeViewIndicator currently shown in the tree
        self._indicators = {}
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

        # Right-click on the toolbar button opens a small reset menu.
        button = self.toolbar.widgetForAction(self.action)
        if button is not None:
            button.setContextMenuPolicy(self._custom_ctx_policy())
            button.customContextMenuRequested.connect(self._show_reset_menu)

        # Keep the action in sync with the active project's persisted state.
        project = QgsProject.instance()
        project.readProject.connect(self._restore_state)
        # cleared was added in QGIS 3.2; guard so we still load on 3.0/3.1.
        if hasattr(project, "cleared"):
            project.cleared.connect(self._restore_state)
            self._cleared_connected = True
        self._restore_state()

        # Per-layer multiply indicators in the layer tree (clickable icon next
        # to each layer). This works independently of the layer-tree context
        # menu, whose contextMenuAboutToShow signal is not emitted in every
        # QGIS build/plugin combination.
        self._connect_tree_signals()
        self._refresh_indicators()

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

        self._disconnect_tree_signals()
        # Suspend refreshes so any QTimer.singleShot already queued cannot
        # re-add indicators after the GUI is torn down.
        self._indicators_enabled = False
        self._clear_indicators()

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

    # --- blend-mode helpers --------------------------------------------------

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
            for child in node.children():
                self.set_blend_mode(child, mode)
        elif isinstance(node, QgsLayerTreeLayer):
            layer = node.layer()
            if layer:
                self._apply_to_layer(layer, mode)

    def _apply_to_layer(self, layer, mode):
        """Set a layer's blend mode, capturing its original once for restore."""
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

    # --- per-project persistence --------------------------------------------

    def _save_state(self):
        """Persist the active flag and captured blend modes into the project.

        Writes only when something actually changed: writeEntry marks the
        project dirty, so skipping no-op writes avoids spurious "unsaved
        changes" prompts.
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
        self._refresh_indicators()

    # --- per-layer indicators ------------------------------------------------

    def _connect_tree_signals(self):
        """Refresh indicators whenever the layer tree structure changes."""
        self._model = self.iface.layerTreeView().model()
        if self._model is not None:
            self._model.rowsInserted.connect(self._schedule_refresh)
            self._model.rowsRemoved.connect(self._schedule_refresh)
            self._model.modelReset.connect(self._schedule_refresh)
            self._model_connected = True

    def _disconnect_tree_signals(self):
        if self._model_connected and self._model is not None:
            for signal in (self._model.rowsInserted,
                           self._model.rowsRemoved,
                           self._model.modelReset):
                try:
                    signal.disconnect(self._schedule_refresh)
                except (TypeError, RuntimeError):
                    pass
        self._model_connected = False
        self._model = None

    def _schedule_refresh(self, *args):
        """Debounce: refresh after the current model change has settled."""
        QTimer.singleShot(0, self._refresh_indicators)

    def _iter_layer_nodes(self, node):
        """Yield every QgsLayerTreeLayer node under the given node."""
        if isinstance(node, QgsLayerTreeLayer):
            yield node
        elif isinstance(node, QgsLayerTreeGroup):
            for child in node.children():
                yield from self._iter_layer_nodes(child)

    def _set_indicator_state(self, indicator, active):
        """Set an indicator's icon/tooltip to reflect the per-layer state."""
        indicator.setIcon(QIcon(self.ICON_ON if active else self.ICON_OFF))
        indicator.setToolTip(
            "Multiply: ON – click to deactivate" if active
            else "Multiply: OFF – click to activate"
        )

    def _refresh_indicators(self):
        """Ensure every layer carries one indicator reflecting its state.

        Idempotent and move/remove safe: existing indicators are updated in
        place (checked via view.indicators(node)); new/moved layers get a fresh
        indicator; removed layers are dropped from tracking (the view releases
        their indicator association automatically).
        """
        # self.action is None after unload; a QTimer.singleShot refresh that was
        # queued just before unload must not re-add indicators on a dead instance.
        if not self._indicators_enabled or self.action is None:
            return
        view = self.iface.layerTreeView()
        root = QgsProject.instance().layerTreeRoot()
        current = set()
        for node in self._iter_layer_nodes(root):
            layer = node.layer()
            if layer is None:
                continue
            lid = layer.id()
            current.add(lid)
            active = lid in self.saved_blend_modes
            ind = self._indicators.get(lid)
            if ind is not None and ind in view.indicators(node):
                self._set_indicator_state(ind, active)
            else:
                ind = QgsLayerTreeViewIndicator(view)
                ind.clicked.connect(
                    lambda idx, layer_id=lid: self._on_indicator_clicked(layer_id)
                )
                self._set_indicator_state(ind, active)
                view.addIndicator(node, ind)
                self._indicators[lid] = ind
        for lid in list(self._indicators):
            if lid not in current:
                del self._indicators[lid]

    def _clear_indicators(self):
        """Remove and delete all our indicators.

        Indicators are parented to the (long-lived) layer-tree view, so they
        must be deleted explicitly — otherwise each load/reload leaks one per
        layer. Detach from live nodes first, then delete every tracked object.
        """
        view = self.iface.layerTreeView()
        nodes_by_id = {}
        for node in self._iter_layer_nodes(QgsProject.instance().layerTreeRoot()):
            layer = node.layer()
            if layer is not None:
                nodes_by_id[layer.id()] = node
        for lid, ind in self._indicators.items():
            if ind is None:
                continue
            node = nodes_by_id.get(lid)
            if node is not None and ind in view.indicators(node):
                view.removeIndicator(node, ind)
            ind.deleteLater()
        self._indicators = {}

    def _on_indicator_clicked(self, layer_id):
        """Toggle multiply for a single layer via its tree indicator."""
        layer = QgsProject.instance().mapLayer(layer_id)
        if layer is None:
            return
        if layer_id in self.saved_blend_modes:
            mode = self._mode_from_int(self.saved_blend_modes[layer_id])
            if mode is not None:
                layer.setBlendMode(mode)
                layer.triggerRepaint()
            del self.saved_blend_modes[layer_id]
            message = f"Multiply removed from '{layer.name()}'."
        else:
            self._apply_to_layer(layer, self._multiply_mode())
            message = f"Multiply applied to '{layer.name()}'."
        # Invariant: the toolbar toggle is "on" iff we hold saved layers.
        self._reflect_state(bool(self.saved_blend_modes))
        self._save_state()
        self._refresh_indicators()
        self.iface.mapCanvas().refresh()
        self._notify(message)

    # --- reset ---------------------------------------------------------------

    def _custom_ctx_policy(self):
        """Return Qt.CustomContextMenu (Qt5/Qt6 safe)."""
        try:
            return Qt.ContextMenuPolicy.CustomContextMenu  # Qt6 / PyQt5>=5.15
        except AttributeError:
            return Qt.CustomContextMenu  # older PyQt5

    def _show_reset_menu(self, pos):
        """Right-click menu on the toolbar button: offer a full reset."""
        button = self.toolbar.widgetForAction(self.action) if self.toolbar else None
        menu = QMenu(self.iface.mainWindow())
        act = menu.addAction("Reset: undo all changes and remove icons")
        act.triggered.connect(self._reset_all)
        anchor = button if button is not None else self.iface.mainWindow()
        global_pos = anchor.mapToGlobal(pos)
        (menu.exec if hasattr(menu, "exec") else menu.exec_)(global_pos)

    def _reset_all(self, *args):
        """Undo everything the plugin did and return to a clean state.

        Restores every layer's original blend mode, clears the persisted
        project entries, removes all per-layer indicators (and suspends them
        until multiply is switched on again) and sets the toggle to off.
        """
        self.restore_blend_modes()  # restore originals + clear saved_blend_modes
        project = QgsProject.instance()
        project.removeEntry(LOG_TAG, "active")
        project.removeEntry(LOG_TAG, "saved_modes")
        self._reflect_state(False)  # toggle off (no signal)
        self._indicators_enabled = False
        self._clear_indicators()  # remove all icons from the layer tree
        self.iface.mapCanvas().refresh()
        self._notify("Reset: original blend modes restored, indicators removed.")

    # --- toolbar toggle ------------------------------------------------------

    def _apply_multiply(self):
        """Apply multiply to the selected nodes, or the whole tree if none.

        Returns a human-readable description of the affected scope.
        """
        root = QgsProject.instance().layerTreeRoot()
        mode = self._multiply_mode()

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
        """
        if checked:
            # a reset may have suspended the indicators; re-enable on activate.
            self._indicators_enabled = True
            self.action.setIcon(QIcon(self.ICON_ON))
            self.action.setToolTip("Multiply mode: ON – click to deactivate")
            self._notify(f"Multiply applied to {self._apply_multiply()}.")
        else:
            self.action.setIcon(QIcon(self.ICON_OFF))
            self.action.setToolTip("Multiply mode: OFF – click to activate")
            self.restore_blend_modes()
            self._notify("Original blend modes restored.")

        self._save_state()
        self._refresh_indicators()
        self.iface.mapCanvas().refresh()
