# 第一阶段使用固定 Node.js 版本构建 Vue 静态资源。
FROM node:22.14.0-alpine3.21 AS build

WORKDIR /web
COPY frontend/package.json ./
# package.json 已锁定直接依赖版本；联网安装后会生成 package-lock.json。
RUN npm install --ignore-scripts
COPY frontend/ ./
RUN npm run build

# 第二阶段只保留 Nginx 与构建产物。
FROM nginx:1.27.4-alpine
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /web/dist /usr/share/nginx/html

EXPOSE 80
