# -----------------------------------------------------------------------------#
# Title:       LayerMultiplyToggle                                             #
# Author:      Mike Elstermann alias mikeE. & #geoObserver                     #
# Version:     v0.3                                                            #
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
from qgis.PyQt.QtWidgets import QToolBar, QToolButton, QMenu
try:
    from qgis.PyQt.QtWidgets import QAction, QActionGroup  # Qt5 / QGIS 3.x
except ImportError:
    from qgis.PyQt.QtGui import QAction, QActionGroup  # Qt6 / QGIS 4.x
from qgis.core import (
    Qgis,
    QgsProject,
    QgsLayerTreeGroup,
    QgsLayerTreeLayer,
    QgsMessageLog,
)

LOG_TAG = "LayerMultiplyToggle"


class LayerMultiplyToggle:

    # (label, QPainter.CompositionMode member name) offered in the dropdown.
    BLEND_MODES = [
        ("Multiply", "CompositionMode_Multiply"),
        ("Screen", "CompositionMode_Screen"),
        ("Overlay", "CompositionMode_Overlay"),
        ("Darken", "CompositionMode_Darken"),
        ("Lighten", "CompositionMode_Lighten"),
    ]

    def __init__(self, iface):
        self.iface = iface
        self.toolbar = None
        self.action = None
        self.mode_group = None
        self._ctx_connected = False
        # qualified QPainter.CompositionMode member name of the active mode
        self.active_mode_name = "CompositionMode_Multiply"
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

        # Attach the blend-mode dropdown to the toolbar's QToolButton: the main
        # button half toggles, the arrow opens the mode menu (split button).
        tool_button = self.toolbar.widgetForAction(self.action)
        if isinstance(tool_button, QToolButton):
            tool_button.setMenu(self._build_mode_menu())
            tool_button.setPopupMode(self._menu_popup_mode())

        # Keep the action in sync with the active project's persisted state.
        QgsProject.instance().readProject.connect(self._restore_state)
        QgsProject.instance().cleared.connect(self._restore_state)
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
        try:
            QgsProject.instance().readProject.disconnect(self._restore_state)
            QgsProject.instance().cleared.disconnect(self._restore_state)
        except (TypeError, RuntimeError):
            pass

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
        self.action = None

        # Only remove toolbar if it is empty after removing our action
        if self.toolbar is not None:
            if len(self.toolbar.actions()) == 0:
                self.iface.mainWindow().removeToolBar(self.toolbar)
                self.toolbar.deleteLater()
            self.toolbar = None

    def _composition_mode(self, enum_name):
        """Resolve a QPainter.CompositionMode member by name (Qt5/Qt6 safe)."""
        try:
            return getattr(QPainter.CompositionMode, enum_name)  # Qt6 / PyQt5>=5.15
        except AttributeError:
            return getattr(QPainter, enum_name)  # older PyQt5 (unscoped enums)

    def _multiply_mode(self):
        """Return the Multiply CompositionMode (Qt5/Qt6 compatible)."""
        return self._composition_mode("CompositionMode_Multiply")

    def _menu_popup_mode(self):
        """Return QToolButton.MenuButtonPopup (Qt5/Qt6 safe)."""
        try:
            return QToolButton.ToolButtonPopupMode.MenuButtonPopup  # Qt6 / PyQt5>=5.15
        except AttributeError:
            return QToolButton.MenuButtonPopup  # older PyQt5

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
                self._apply_to_layer(layer, mode)

    def _apply_to_layer(self, layer, mode):
        """Set a layer's blend mode, capturing its original once for restore.

        The original is stored as int (keyed by layer id) so it can be
        persisted to the project and restored later.
        """
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
        project.writeEntry(LOG_TAG, "mode", self.active_mode_name)
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
        self.active_mode_name = project.readEntry(
            LOG_TAG, "mode", "CompositionMode_Multiply"
        )[0] or "CompositionMode_Multiply"
        self._sync_mode_menu()
        self._reflect_state(active)

    def _build_mode_menu(self):
        """Build the blend-mode dropdown menu for the toolbar button."""
        menu = QMenu(self.iface.mainWindow())
        menu.setSeparatorsCollapsible(False)
        self.mode_group = QActionGroup(menu)
        self.mode_group.setExclusive(True)
        for label, enum_name in self.BLEND_MODES:
            act = menu.addAction(label)
            act.setCheckable(True)
            act.setData(enum_name)
            act.setChecked(enum_name == self.active_mode_name)
            self.mode_group.addAction(act)
        self.mode_group.triggered.connect(self._on_mode_chosen)

        menu.addSeparator()
        apply_sel = menu.addAction("Apply to current selection")
        apply_sel.triggered.connect(self._apply_to_selection_now)
        return menu

    def _sync_mode_menu(self):
        """Check the menu item matching the active mode (no signal side effect)."""
        if self.mode_group is None:
            return
        for act in self.mode_group.actions():
            act.setChecked(act.data() == self.active_mode_name)

    def _on_mode_chosen(self, act):
        """Set the active blend mode; re-apply live if multiply is on."""
        enum_name = act.data()
        if not enum_name:
            return
        self.active_mode_name = enum_name
        if self.action is not None and self.action.isChecked() and self.saved_blend_modes:
            mode = self._composition_mode(enum_name)
            project = QgsProject.instance()
            for layer_id in self.saved_blend_modes:
                layer = project.mapLayer(layer_id)
                if layer:
                    layer.setBlendMode(mode)
                    layer.triggerRepaint()
            self.iface.mapCanvas().refresh()
            self._notify(f"Blend mode changed to {act.text()}.")
        self._save_state()

    def _apply_to_selection_now(self, *args):
        """Extend the active blend mode to the current selection without a toggle."""
        if self.action is not None and not self.action.isChecked():
            # Not active yet: turning the action on applies + saves + persists.
            self.action.setChecked(True)
            return
        scope = self._apply_multiply()
        self._save_state()
        self.iface.mapCanvas().refresh()
        self._notify(f"Blend mode applied to {scope}.")

    def _mode_label(self):
        """Human-readable label of the currently active blend mode."""
        for label, enum_name in self.BLEND_MODES:
            if enum_name == self.active_mode_name:
                return label
        return "Multiply"

    def _node_layer_ids(self, nodes):
        """Collect the layer ids under the given layer-tree nodes (recursive)."""
        ids = []

        def walk(node):
            if isinstance(node, QgsLayerTreeGroup):
                for child in node.children():
                    walk(child)
            elif isinstance(node, QgsLayerTreeLayer):
                layer = node.layer()
                if layer:
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
        apply_act = sub.addAction(f"Apply {self._mode_label()}")
        apply_act.triggered.connect(
            lambda checked=False, ids=layer_ids: self._ctx_apply(ids)
        )
        restore_act = sub.addAction("Restore original blend mode")
        restore_act.setEnabled(any(i in self.saved_blend_modes for i in layer_ids))
        restore_act.triggered.connect(
            lambda checked=False, ids=layer_ids: self._ctx_restore(ids)
        )

    def _ctx_apply(self, layer_ids):
        """Apply the active blend mode to the given layers (from context menu)."""
        mode = self._composition_mode(self.active_mode_name)
        project = QgsProject.instance()
        count = 0
        for layer_id in layer_ids:
            layer = project.mapLayer(layer_id)
            if layer:
                self._apply_to_layer(layer, mode)
                count += 1
        self._save_state()
        self.iface.mapCanvas().refresh()
        self._notify(f"{self._mode_label()} applied to {count} layer(s).")

    def _ctx_restore(self, layer_ids):
        """Restore the original blend mode for the given layers (context menu)."""
        project = QgsProject.instance()
        count = 0
        for layer_id in layer_ids:
            if layer_id in self.saved_blend_modes:
                layer = project.mapLayer(layer_id)
                if layer:
                    layer.setBlendMode(self._mode_from_int(self.saved_blend_modes[layer_id]))
                    layer.triggerRepaint()
                del self.saved_blend_modes[layer_id]
                count += 1
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
        mode = self._composition_mode(self.active_mode_name)

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
