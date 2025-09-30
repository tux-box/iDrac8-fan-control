#!/bin/sh
set -e

echo "Starting iDRAC Fan Control in $MODE mode..."
exec python3 fancontrol.py
