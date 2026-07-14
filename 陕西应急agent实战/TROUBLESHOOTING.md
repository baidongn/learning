# 故障排查

## 测试找不到包

必须从对应周目录先执行 `make setup`。每周是独立快照，不要把某周 `.venv` 复制到另一周。

## PostgreSQL 或 Redis 未就绪

```bash
docker compose -f compose.dev.yaml ps
docker compose -f compose.dev.yaml logs postgres
docker compose -f compose.dev.yaml logs redis
```

确认 5432/6379 未被占用，再运行 `make migrate`。pgvector 扩展由 Alembic 初始迁移创建。

## DeepSeek 调用失败

先切回 `MODEL_MODE=mock` 确认业务测试通过，再检查 Key、Base URL、模型名、余额和网络。不要在日志中打印 Authorization Header。Live 结构不合法时会明确报“DeepSeek 返回的预案建议不符合结构化契约”。

## npm 安装失败

Week 10 起首次安装需要访问 npm registry。检查代理、DNS 和 Node.js 版本；成功后保留生成的 `package-lock.json`。无网络时仍可先完成全部后端测试。

## Docker Compose 配置在受限沙箱报缓存错误

普通本机不会受影响。受限执行环境可把 `HOME` 指向可写目录，同时把 `DOCKER_CONFIG` 指向已有 Docker 配置目录。

## Kustomize 失败

先只渲染，不急着 apply：

```bash
kubectl kustomize deploy/k8s/base
kubectl kustomize deploy/k8s/overlays/dev
kubectl kustomize deploy/k8s/overlays/prod
```

检查补丁目标名称、namespace、Secret 名称和镜像名称是否与 base 一致。
