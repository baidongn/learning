# 开始学习

## 1. 本地环境

必需：Python 3.11+、Docker 24+、Docker Compose、GNU Make。Week 1–3 的锁文件使用 uv；Week 10 起还需要 Node.js 20.19+。Week 12 的 Kubernetes 练习需要 kubectl 与 kind。

```bash
python3 --version
python3 -m pip install uv
docker --version
docker compose version
node --version
```

## 2. 每周固定顺序

```bash
cd weeks/week-01          # 换成本周目录
cp .env.example .env
make setup
make infra-up             # 需要数据库时执行
make migrate              # 需要表结构时执行
make test
make run
```

完成课程中的唯一作业后执行：

```bash
make eval
make verify
```

先读 `README.md` 看结果，再读 `WEEK-XX-COURSE.md` 动手。每周只完成“必做”，有余力再做“选做”。

## 3. DeepSeek 模式

Mock 是默认值，结果确定、无费用、适合测试：

```dotenv
MODEL_MODE=mock
```

Live 模式的预案专家会先检索课程预案，再调用 DeepSeek 生成 JSON 建议；引用由代码绑定，模型不能自行伪造：

```dotenv
MODEL_MODE=live
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_API_KEY=your-key
DEEPSEEK_MODEL=deepseek-v4-flash
```

不要把 Key 提交到 Git。模型接口与可用模型以 DeepSeek 官方文档为准：<https://api-docs.deepseek.com/>。

## 4. 本地数据库

```bash
make infra-up
docker compose -f compose.dev.yaml ps
make migrate
```

本地默认启动 PostgreSQL/pgvector 与 Redis。生产部署不会在应用 Pod 中内置数据库，详见 `DEPLOY_DOCKER.md` 和 `DEPLOY_K8S.md`。
