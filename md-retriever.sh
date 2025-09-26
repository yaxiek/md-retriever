#!/usr/bin/env bash
# md-retriever.sh — 手動実行用ランチャー（gitignoreは無視）
# 使い方:
#   ./md-retriever.sh <dir> [--config path/to/config.toml] [Python側オプション...]
# 例:
#   ./md-retriever.sh . --config ./config.toml --exclude .obsidian --output README.md

set -euo pipefail

if [[ "${1:-}" == "" ]]; then
    echo "usage: $(basename "$0") <dir> [--config CONFIG_TOML] [--more-python-options]"
    exit 1
fi

ROOT="$1"; shift || true

# スクリプトの隣にある md_retriever.py を呼ぶ
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${PYTHON:-python3}"   # 環境変数 PYTHON で差し替え可

exec "$PY" "$SCRIPT_DIR/md_retriever.py" "$ROOT" "$@"