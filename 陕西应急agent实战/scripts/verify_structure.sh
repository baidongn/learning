#!/usr/bin/env bash
set -euo pipefail

# 检查每周是否包含独立学习所需的代码、课程、评测和预期截图。
for number in $(seq -w 1 12); do
  week="weeks/week-${number}"
  course="${week}/WEEK-${number}-COURSE.md"
  test -f "${week}/README.md"
  test -f "${week}/CHANGELOG.md"
  test -f "${week}/Makefile"
  test -f "${week}/.env.example"
  test -d "${week}/backend/src"
  test -d "${week}/backend/tests"
  test -f "${week}/tests/README.md"
  test -d "${week}/data"
  test -d "${week}/evals"
  test -f "${week}/docs/expected-output.svg"
  test -f "${course}"
  section_count=$(rg -c '^## [0-9]+\.' "${course}")
  test "${section_count}" -eq 12
  printf 'week-%s structure: ok\n' "${number}"
done

# 渐进目录从指定周开始出现，避免提前增加学习负担。
test -d weeks/week-07/mcp-servers
test -d weeks/week-10/frontend
test -d weeks/week-12/deploy/k8s/base
test -d weeks/week-12/deploy/k8s/overlays/dev
test -d weeks/week-12/deploy/k8s/overlays/prod
