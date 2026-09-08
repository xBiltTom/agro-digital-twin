#!/usr/bin/env bash
set -euo pipefail

# User-owned local PostgreSQL runtime for the MVP. No Docker or system service.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DATA_DIR="${BACKEND_DIR}/.local-postgres"
SOCKET_DIR="${MVP_PG_SOCKET_DIR:-/tmp/from-plant-to-watershed-pg}"
PORT="${MVP_PG_PORT:-55432}"
DATABASE="${MVP_PG_DATABASE:-digitaltwin}"

mkdir -p "${SOCKET_DIR}"
if [[ ! -f "${DATA_DIR}/PG_VERSION" ]]; then
  initdb -D "${DATA_DIR}" --no-locale --encoding=UTF8 --auth=trust
fi
if ! pg_ctl -D "${DATA_DIR}" status >/dev/null 2>&1; then
  pg_ctl -D "${DATA_DIR}" -o "-c listen_addresses='' -p ${PORT} -k ${SOCKET_DIR}" -w start
fi
if ! psql -h "${SOCKET_DIR}" -p "${PORT}" -d postgres -Atqc "SELECT 1 FROM pg_database WHERE datname='${DATABASE}'" | rg -qx '1'; then
  createdb -h "${SOCKET_DIR}" -p "${PORT}" "${DATABASE}"
fi
printf 'PostgreSQL local ready: postgresql+asyncpg://%s@/%s?host=%s&port=%s\n' "${USER}" "${DATABASE}" "${SOCKET_DIR}" "${PORT}"
