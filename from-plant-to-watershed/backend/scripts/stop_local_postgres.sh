#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
pg_ctl -D "$(cd "${SCRIPT_DIR}/.." && pwd)/.local-postgres" -w stop
