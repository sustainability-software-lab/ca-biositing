#!/bin/bash
# Extract version from pixi.toml
grep -m 1 "version =" pixi.toml | cut -d '"' -f 2
