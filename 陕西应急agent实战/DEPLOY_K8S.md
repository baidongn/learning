# Kubernetes / Kustomize 部署

清单位于 `weeks/week-12/deploy/k8s`：

- `base`：Namespace、ConfigMap、Secret 生成器、API/Web Deployment 与 Service。
- `overlays/dev`：额外部署单实例 pgvector 与 Redis，适合 kind。
- `overlays/prod`：只调整镜像、副本、资源与外部连接串，不部署数据库。

## 1. 静态验证

```bash
cd weeks/week-12
kubectl kustomize deploy/k8s/overlays/dev >/tmp/highway-dev.yaml
kubectl kustomize deploy/k8s/overlays/prod >/tmp/highway-prod.yaml
```

## 2. kind 本地部署

```bash
docker build -f backend/Dockerfile -t shaanxi-highway-agent-api:0.12.0 .
docker build -f frontend/Dockerfile -t shaanxi-highway-agent-web:0.12.0 .
kind create cluster --name highway-agent
kind load docker-image shaanxi-highway-agent-api:0.12.0 --name highway-agent
kind load docker-image shaanxi-highway-agent-web:0.12.0 --name highway-agent
kubectl apply -k deploy/k8s/overlays/dev
kubectl -n highway-agent rollout status deployment/highway-agent-api
kubectl -n highway-agent rollout status deployment/highway-agent-web
kubectl -n highway-agent port-forward service/web 8080:80
```

dev 环境的 API Pod initContainer 会执行幂等的 `alembic upgrade head`。访问 `http://localhost:8080` 完成默认案例冒烟测试。

删除 kind 集群：

```bash
kind delete cluster --name highway-agent
```

## 3. 生产准备

1. 把 prod overlay 的 `ghcr.io/your-name/...` 改成真实仓库和不可变标签。
2. 删除示例 Secret literals，改用组织的 Secret Manager/External Secrets 或部署流水线注入。
3. 注入外部 PostgreSQL/pgvector 与 Redis 地址，并先验证备份和网络连通。
4. prod overlay 使用唯一的 `highway-agent-migrate` Job，API Pod 不再各自迁移；发布流水线应等待 Job 完成后再确认 API rollout。重复发布前删除已完成的旧 Job，或为 Job 使用新的发布名。
5. 根据负载补充 Ingress、TLS、HPA、PDB 和 NetworkPolicy；课程不伪造这些生产策略。
6. 执行 `kubectl diff -k ...` 后再 apply，使用 `kubectl rollout undo` 回滚 Deployment。

生产发布的关键等待命令：

```bash
kubectl apply -k deploy/k8s/overlays/prod
kubectl -n highway-agent wait --for=condition=complete job/highway-agent-migrate --timeout=180s
kubectl -n highway-agent rollout status deployment/highway-agent-api
```

当前仓库保证 base/dev/prod 可以渲染；实际 kind apply 需要本机已安装 kind 且可以拉取固定镜像。
