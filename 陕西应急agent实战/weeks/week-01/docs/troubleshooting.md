# Week 1 排障

优先执行 `docker compose -f compose.dev.yaml ps` 和 `logs postgres`。若希望完全重建本地数据，执行 `make reset` 后重新 `make infra-up && make migrate`。该操作会删除本周本地卷，请勿用于真实数据。

