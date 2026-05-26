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

import os
from qgis.PyQt.QtGui import QPainter, QIcon
from qgis.PyQt.QtWidgets import QToolBar
try:
    from qgis.PyQt.QtWidgets import QAction  # Qt5 / QGIS 3.x
except ImportError:
    from qgis.PyQt.QtGui import QAction  # Qt6 / QGIS 4.x
from qgis.core import QgsProject, QgsLayerTreeGroup, QgsLayerTreeLayer


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

    def initGui(self):
        """Initialize the plugin GUI."""

        # Find or create toolbar
        self.toolbar = self.iface.mainWindow().findChild(QToolBar, "geoObserverTools")
        if self.toolbar is None:
            self.toolbar = QToolBar("geoObserverTools")
            self.toolbar.setObjectName("geoObserverTools")
            self.iface.mainWindow().addToolBar(self.toolbar)
            print("Toolbar 'geoObserverTools' created.")
        else:
            print("Toolbar 'geoObserverTools' found.")

        # Create a checkable action; QToolBar renders it as a themed
        # QToolButton that honours the QGIS icon size and dark/light theme.
        self.action = QAction(QIcon(self.ICON_OFF), "Multiply blend mode",
                              self.iface.mainWindow())
        self.action.setCheckable(True)
        self.action.setToolTip("Multiply mode: OFF – click to activate")
        self.action.toggled.connect(self.toggle_multiply)

        self.toolbar.addAction(self.action)
        print("Multiply button ready in toolbar 'geoObserverTools'.")

    def unload(self):
        """Remove the plugin GUI on unload."""
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

    def get_composition_mode(self, mode):
        """Returns the correct CompositionMode for Qt5 and Qt6."""
        try:
            # Qt6 / QGIS 4.x
            if mode == "multiply":
                return QPainter.CompositionMode.CompositionMode_Multiply
            else:
                return QPainter.CompositionMode.CompositionMode_SourceOver
        except AttributeError:
            # Qt5 / QGIS 3.x
            if mode == "multiply":
                return QPainter.CompositionMode_Multiply
            else:
                return QPainter.CompositionMode_SourceOver

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
                # Remember the original mode once so toggling off can
                # restore it instead of clobbering it with "normal".
                if layer.id() not in self.saved_blend_modes:
                    self.saved_blend_modes[layer.id()] = layer.blendMode()
                layer.setBlendMode(mode)
                layer.triggerRepaint()

    def restore_blend_modes(self):
        """Restore the blend modes captured when multiply was activated."""
        project = QgsProject.instance()
        for layer_id, original_mode in self.saved_blend_modes.items():
            layer = project.mapLayer(layer_id)
            if layer:
                layer.setBlendMode(original_mode)
                layer.triggerRepaint()
        self.saved_blend_modes.clear()

    def toggle_multiply(self, checked):
        """Toggle multiply blend mode for selected or all layers."""
        if checked:
            self.action.setIcon(QIcon(self.ICON_ON))
            self.action.setToolTip("Multiply mode: ON – click to deactivate")
        else:
            self.action.setIcon(QIcon(self.ICON_OFF))
            self.action.setToolTip("Multiply mode: OFF – click to activate")

        if checked:
            root = QgsProject.instance().layerTreeRoot()
            multiply_mode = self.get_composition_mode("multiply")

            # Selected layers/groups take precedence; otherwise the whole tree.
            selected_nodes = self.iface.layerTreeView().selectedNodes()
            target_nodes = selected_nodes if selected_nodes else root.children()
            for node in target_nodes:
                self.set_blend_mode(node, multiply_mode)

            if selected_nodes:
                print(f"{len(selected_nodes)} selected layer(s)/group(s) processed.")
            else:
                print("All layers processed.")
        else:
            # Restore exactly the layers we changed, back to their real
            # previous modes, regardless of the current selection.
            self.restore_blend_modes()
            print("Original blend modes restored.")

        self.iface.mapCanvas().refresh()
