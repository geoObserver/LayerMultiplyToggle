# -----------------------------------------------------------------------------#
# Title:       LayerMultiplyToggle                                             #
# Author:      Mike Elstermann alias mikeE. & #geoObserver                     #
# Version:     v0.1                                                            #
# Created:     21.02.2026                                                      #
# Last Change: 23.02.2026                                                      #
# see also:    https://geoobserver.de/qgis-plugins/                            #
#                                                                              #
# This file contains code generated with assistance from an AI (Claude.ai)     #
# No warranty is provided for AI-generated portions.                           #
# Human review and modification performed by: Mike Elstermann (#geoObserver)   #
# -----------------------------------------------------------------------------#

def classFactory(iface):
    from .LayerMultiplyToggle import LayerMultiplyToggle
    return LayerMultiplyToggle(iface)
