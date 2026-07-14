# 固定基础镜像版本，课程和 CI 都不使用 latest。
FROM python:3.11.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}"

WORKDIR /app

# 先复制固定版本依赖清单以复用 Docker 构建缓存。
COPY backend/requirements.lock.txt ./
RUN python -m pip install --no-cache-dir -r requirements.lock.txt

COPY backend/alembic.ini ./alembic.ini
COPY backend/alembic ./alembic
COPY backend/src ./src

EXPOSE 8000
CMD ["uvicorn", "highway_agent.main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]
