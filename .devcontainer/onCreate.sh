#!/bin/bash

# For writing commands that will be executed after the container is created
set -e

sudo chown vscode .pixi

# Install the default environment only.
# GIS environment (QGIS) is intentionally excluded — install manually with:
#   pixi install -e gis
# if you need QGIS or heavy raster/vector tools.
pixi install -e default
