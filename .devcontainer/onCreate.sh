#!/bin/bash

# For writing commands that will be executed after the container is created
set -e

# Increase file descriptor limit to prevent EMFILE errors
ulimit -n 65536

sudo chown vscode .pixi

# Install core development and ETL environments
# Skip resource-heavy environments like 'gis' (QGIS) to save space and time in Codespaces
pixi install -e default -e etl -e webservice
