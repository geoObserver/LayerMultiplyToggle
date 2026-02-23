# -----------------------------------------------------------------------------#
# Title:       LayerMultiplyToggle                                             #
# Author:      Mike Elstermann alias mikeE. & #geoObserver                     #
# Version:     v0.1                                                            #
# Created:     21.02.2026                                                      #
# Last Change: 22.02.2026                                                      #
# see also:    https://geoobserver.de/qgis-plugins/                            #
#                                                                              #
# This file contains code generated with assistance from an AI (Claude.ai)     #
# No warranty is provided for AI-generated portions.                           #
# Human review and modification performed by: Mike Elstermann (#geoObserver)   #
# -----------------------------------------------------------------------------#

import os
from qgis.PyQt.QtGui import QPainter, QIcon
from qgis.PyQt.QtWidgets import QPushButton, QToolBar
from qgis.PyQt.QtCore import QSize
from qgis.core import QgsProject, QgsLayerTreeGroup, QgsLayerTreeLayer


class LayerMultiplyToggle:

    def __init__(self, iface):
        self.iface = iface
        self.toolbar = None
        self.button = None
        self.plugin_dir = os.path.dirname(__file__)

        # Icon paths (bundled with plugin)
        self.ICON_OFF = os.path.join(self.plugin_dir, "icons", "multiply_layers_icon_noactive.png")
        self.ICON_ON  = os.path.join(self.plugin_dir, "icons", "multiply_layers_icon_active.png")

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

        # Create button
        self.button = QPushButton()
        self.button.setCheckable(True)
        self.button.setIcon(QIcon(self.ICON_OFF))
        self.button.setFixedSize(QSize(28, 28))
        self.button.setIconSize(QSize(24, 24))
        self.button.setStyleSheet("""
            QPushButton {
                border: 0px;
                padding: 2px;
                background-color: transparent;
            }
            QPushButton:hover {
                background-color: rgba(128, 128, 128, 40);
            }
        """)
        self.button.setToolTip("Multiply mode: OFF – click to activate")
        self.button.toggled.connect(self.toggle_multiply)

        self.toolbar.addWidget(self.button)
        print("Multiply button ready in toolbar 'geoObserverTools'.")

    def unload(self):
        """Remove the plugin GUI on unload."""
        if self.button is not None:
            self.button.deleteLater()
            self.button = None

        # Only remove toolbar if it is empty after removing our button
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
            node.setCustomProperty("rendering/blendMode", mode)
            for child in node.children():
                self.set_blend_mode(child, mode)
        elif isinstance(node, QgsLayerTreeLayer):
            layer = node.layer()
            if layer:
                layer.setBlendMode(mode)
                layer.triggerRepaint()

    def toggle_multiply(self, checked):
        """Toggle multiply blend mode for selected or all layers."""
        root = QgsProject.instance().layerTreeRoot()
        mode = self.get_composition_mode("multiply") if checked else self.get_composition_mode("normal")

        if checked:
            self.button.setIcon(QIcon(self.ICON_ON))
            self.button.setToolTip("Multiply mode: ON – click to deactivate")
        else:
            self.button.setIcon(QIcon(self.ICON_OFF))
            self.button.setToolTip("Multiply mode: OFF – click to activate")

        # Check for selected layers in the layer panel
        selected_nodes = self.iface.layerTreeView().selectedNodes()

        if selected_nodes:
            for node in selected_nodes:
                self.set_blend_mode(node, mode)
            print(f"{len(selected_nodes)} selected layer(s)/group(s) processed.")
        else:
            for child in root.children():
                self.set_blend_mode(child, mode)
            print("All layers processed.")

        self.iface.mapCanvas().refresh()
