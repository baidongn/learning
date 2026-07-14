# Week 12：Docker、Kubernetes 与项目包装

这是最终可交付快照。包含 5 个 Agent、模拟 REST/MCP Tool、RAG、LangGraph/HITL、Vue 指挥台、评测、Docker 和 Kustomize。

## Docker 一条命令演示

```bash
cp .env.example .env
make run
```

打开 `http://localhost:8080`。默认 `MODEL_MODE=mock`，无需 DeepSeek Key。停止环境执行 `make infra-down`。

## Kubernetes

```bash
kubectl kustomize deploy/k8s/overlays/dev
kubectl kustomize deploy/k8s/overlays/prod
```

kind 完整步骤见根目录 `DEPLOY_K8S.md`。生产 overlay 不部署 PostgreSQL/Redis，必须使用外部服务并替换示例 Secret 与镜像仓库。

验收：`make test`、`make eval`、`make verify`。课程正文见 `WEEK-12-COURSE.md`。
