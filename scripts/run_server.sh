#!/usr/bin/env bash
set -euo pipefail
uvicorn server.app.main:app --host 0.0.0.0 --port 8000 --reload
