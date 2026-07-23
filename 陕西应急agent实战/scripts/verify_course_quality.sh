#!/usr/bin/env bash
set -euo pipefail

if test "$#" -eq 1; then
  numbers="$(printf '%02d' "$((10#$1))")"
else
  numbers="$(seq -w 1 12)"
fi

for number in ${numbers}; do
  course="weeks/week-${number}/WEEK-${number}-COURSE.md"
  test -f "${course}"

  section_count=$(rg -c '^## [0-9]+\.' "${course}")
  test "${section_count}" -eq 12

  line_count=$(wc -l <"${course}")
  test "${line_count}" -ge 700

  for day in 1 2 3 4 5; do
    day_heading_count=$(rg -c "^## [4-8]\. Day ${day}：" "${course}")
    test "${day_heading_count}" -eq 1

    subsection_count=$(awk -v day="${day}" '
      $0 ~ "^## [4-8]\\. Day " day "：" { inside=1; next }
      inside && /^## / { inside=0 }
      inside && /^### / { count++ }
      END { print count + 0 }
    ' "${course}")
    test "${subsection_count}" -ge 8
  done

  fence_count=$(rg -c '^```' "${course}")
  test "$((fence_count % 2))" -eq 0
  test "${fence_count}" -gt 0

  test "$(rg -c '^### 今天目标' "${course}")" -eq 5
  test "$(rg -c '^### .*预期输出' "${course}")" -ge 5
  test "$(rg -c '^### 当天小练习' "${course}")" -eq 5
  test "$(rg -c '^### 面试题 [123]' "${course}")" -eq 3
  rg -q 'make test' "${course}"
  rg -q 'make eval' "${course}"
  rg -q 'make verify' "${course}"

  printf 'week-%s course quality: ok\n' "${number}"
done
