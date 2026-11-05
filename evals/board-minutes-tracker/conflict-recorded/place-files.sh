#!/usr/bin/env bash
# Copies this case's synthetic input files into the empty eval workspace.
set -euo pipefail
CASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -R "$CASE_DIR/files/." .
