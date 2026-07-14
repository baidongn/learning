#!/usr/bin/env bash
set -euo pipefail

python_bin="${PYTHON_BIN:-.venv/bin/python}"
test -x "${python_bin}"

# 使用根验证环境逐周运行，证明每个累计快照都能独立导入和测试。
for number in $(seq -w 1 12); do
  printf '\n== week-%s backend tests ==\n' "${number}"
  "${python_bin}" -m pytest -q "weeks/week-${number}/backend/tests"
done

# npm 依赖已安装时同时验证三个前端快照；无网络环境给出明确提示。
for number in 10 11 12; do
  frontend="weeks/week-${number}/frontend"
  if test -x "${frontend}/node_modules/.bin/vitest"; then
    (cd "${frontend}" && npm run test:run && npm run build)
  else
    printf 'week-%s frontend: skipped (run make setup with npm network first)\n' "${number}"
  fi
done
