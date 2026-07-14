# Week 10：Vue 轻量指挥台

本周只增加一个求职演示用单页指挥台：事件录入、辅助决策结果、四 Agent 轨迹和人工审批状态。无登录、无地图 SDK、无复杂后台。

## 快速开始

```bash
cp .env.example .env
make setup
```

分别启动两个终端：

```bash
make run-backend
make run-frontend
```

打开 `http://localhost:5173`，默认秦岭隧道案例可直接提交。运行 `make test`、`make eval`、`make verify` 验收。若首次安装前端依赖，需要本机能够访问 npm registry。

前端入口：`frontend/src/App.vue`。设计说明见 `docs/command-console-design.md`，课程正文见 `WEEK-10-COURSE.md`。
