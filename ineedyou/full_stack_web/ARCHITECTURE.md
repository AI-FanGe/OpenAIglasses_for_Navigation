# AI Glass Full Stack Web System 架构与文件功能说明

本文件详细说明 `ineedyou/full_stack_web` 文件夹中各个文件与目录的具体功能与职责。

## 目录结构概览

```text
ineedyou/full_stack_web/
├── docker-compose.yml     # Docker 编排配置，一键启动整个系统的核心文件
├── README.md              # 简要使用说明与启动指南
├── ARCHITECTURE.md        # 本文件，详细的架构与文件功能说明
├── backend/               # 后端目录 (Django + Django REST Framework)
└── frontend/              # 前端目录 (React + Vite + Material UI)
```

---

## 1. 后端 (Backend - Django)

后端主要负责处理业务逻辑、数据库交互以及提供前端所需的 RESTful API。

*   **`backend/Dockerfile`**
    *   **功能**: 定义后端容器的构建过程。
    *   **行为**: 基于 Python 3.9，安装 `requirements.txt` 中的依赖，并设置执行 `entrypoint.sh` 脚本作为启动入口。
*   **`backend/requirements.txt`**
    *   **功能**: 列出后端项目所需的所有 Python 第三方库（如 django, djangorestframework, psycopg2 等）。
*   **`backend/manage.py`**
    *   **功能**: Django 项目的标准命令行工具，用于执行数据库迁移、运行开发服务器、创建应用等。
*   **`backend/entrypoint.sh`**
    *   **功能**: 后端容器的启动脚本。
    *   **行为**:
        1. 轮询等待 PostgreSQL 数据库启动就绪。
        2. 自动执行数据库迁移 (`makemigrations` 和 `migrate`)。
        3. **自动创建默认的系统管理员 (`admin`) 和普通用户 (`user1`)，并重置他们的密码确保可登录，同时为他们生成 API Token。**
        4. 启动 Django 服务。

### 后端子模块 (Apps)

#### `backend/config/` (主配置)
*   **`settings.py`**: Django 核心配置文件，包含数据库连接信息 (读取 Docker 环境变量)、跨域设置 (CORS)、已安装的 App 列表等。
*   **`urls.py`**: 主路由文件，将 API 请求分发到 `users` 和 `devices` 模块，并配置了 Swagger API 接口文档路由。
*   **`wsgi.py` / `asgi.py`**: Web 服务器网关接口，用于生产环境部署。

#### `backend/users/` (用户与认证)
*   **`models.py`**: 继承了 Django 的默认 User 模型，用于区分管理员 (Admin) 和普通用户。
*   **`views.py`**: 提供登录接口 (`CustomAuthToken`)，验证账号密码并返回 Token；提供用户信息获取接口 (`UserInfoView`)。
*   **`urls.py`**: 定义认证相关的路由（如 `/api/auth/login/`）。

#### `backend/devices/` (设备与日志管理)
*   **`models.py`**:
    *   `Device`: 定义 AI 眼镜设备的数据结构（设备ID、名称、所属用户、在线状态等）。
    *   `DeviceLog`: 定义设备上传的日志结构（时间戳、日志级别、OCR文本等记录）。
*   **`serializers.py`**: 数据序列化器，负责将 Django 模型对象与 JSON 数据相互转换，供 API 使用。
*   **`views.py`**: 提供设备与日志的增删改查 API 接口。内置权限控制：管理员可查看所有数据，普通用户只能查看绑定到自己账号的设备与日志。
*   **`urls.py`**: 定义设备管理的路由（如 `/api/devices/` 和 `/api/logs/`）。

---

## 2. 前端 (Frontend - React)

前端主要负责与用户进行交互，展示数据并调用后端 API。

*   **`frontend/Dockerfile`**
    *   **功能**: 定义前端容器的多阶段构建过程。
    *   **行为**: 第一阶段使用 Node.js 编译 React TypeScript 代码；第二阶段将编译好的静态文件放入 Nginx 服务器中进行部署。
*   **`frontend/nginx.conf`**
    *   **功能**: Nginx 配置文件，用于处理单页应用 (SPA) 的路由回退机制，确保在直接访问子路由时不会报 404 错误。
*   **`frontend/package.json` / `package-lock.json`**
    *   **功能**: Node.js 项目配置文件，定义了项目依赖（React, Material UI, Axios 等）以及打包脚本 (`npm run build`)。
*   **`frontend/vite.config.ts`**
    *   **功能**: Vite 构建工具的配置文件，提供极速的冷启动和热更新功能。
*   **`frontend/tsconfig.json` / `tsconfig.node.json`**
    *   **功能**: TypeScript 编译器的配置文件，确保代码的类型安全。

### 前端源码 (`frontend/src/`)

*   **`main.tsx`**
    *   **功能**: React 应用的入口文件。
    *   **行为**: 挂载根组件，并全局注入 Material UI 的暗色主题 (Dark Theme)。
*   **`App.tsx`**
    *   **功能**: 主组件，负责整个前端的路由配置 (React Router)。
    *   **行为**: 定义了 `/login` 和 `/` (Dashboard) 路由，并通过 `PrivateRoute` 保护需要登录的页面。
*   **`context/AuthContext.tsx`**
    *   **功能**: 全局状态管理 (React Context)。
    *   **行为**: 管理用户的登录状态、存储 Token、从后端拉取用户信息，并提供全局可用的 `login` 和 `logout` 函数。

### 前端页面 (`frontend/src/pages/`)

*   **`Login.tsx`**
    *   **功能**: 用户登录页面。
    *   **行为**: 渲染登录表单，收集用户名和密码，调用 `AuthContext` 的 `login` 方法向后端发起请求。如果失败会显示 "Invalid credentials"。
*   **`Dashboard.tsx`**
    *   **功能**: 主控制台页面。
    *   **行为**: 登录成功后跳转至此。根据用户角色 (Admin 或 User) 展示不同的欢迎语。向后端请求 `/api/devices/` 和 `/api/logs/` 接口，并将获取到的设备列表和操作日志渲染到 Material UI 的数据表格中。

---

## 3. 部署与运行 (Docker Compose)

*   **`docker-compose.yml`**
    *   **功能**: 容器编排文件，负责将上述前后端及数据库串联起来。
    *   **定义了三个服务**:
        1.  **`db`**: 运行 PostgreSQL 15 数据库。将数据持久化挂载到 `postgres_data` volume 中，防止重启数据丢失。
        2.  **`backend`**: 构建后端镜像并运行。暴露 `8000` 端口，连接到 `db` 服务，并注入连接数据库所需的账号密码环境变量。
        3.  **`frontend`**: 构建前端 Nginx 镜像并运行。暴露 `3000` 端口供浏览器访问。
    *   **依赖关系**: `frontend` 等待 `backend` 启动，`backend` 等待 `db` 就绪 (`healthcheck`)。实现了一条命令稳定启动。
