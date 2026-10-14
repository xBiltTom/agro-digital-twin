#!/bin/sh
set -eu
# One process and bounded numerical threads for the 512 MB service.
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-1}"
python deployment/swat_runtime.py install
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1
