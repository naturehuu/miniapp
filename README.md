# 微信小程序面试模拟系统（MVP）

本项目包含三个部分：

- `miniprogram/`：微信小程序前端（原生 WXML + WXSS + JS）
- `backend/`：Python Flask 后端接口（题目、评分、建议）
- `web-frontend/`：Web 前端（静态 HTML/CSS/JS）

## 1. 功能覆盖

- 岗位选择（内置多个岗位，可继续扩展）
- 按岗位加载固定面试问题（所有用户一致）
- 学生逐题输入回答
- 提交后返回：
  - 每题分数（0~100）
  - 平均分
  - 岗位适配度
- 再请求改进建议接口，返回每题优化建议
- 提供题库管理入口（AI 生成 + 人工编辑 + 保存）

后端支持两种模式：

- 配置大模型后，调用模型进行评分与建议
- 未配置模型时，使用本地兜底规则评分（便于离线演示）

## 2. 后端启动

### 2.1 安装依赖

```bash
cd /Users/hh/Documents/work/miniapp/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2.2 环境变量

```bash
cp .env.example .env
```

可按需配置：

- `LLM_PROVIDER`：`mock` / `openai` / `deepseek` / `qwen` / `hunyuan`
- 对应 Provider 的 API Key 与 Base URL（见 `.env.example`）

未配置 API Key 时会自动使用本地兜底逻辑。

### 2.3 运行

```bash
python app.py
```

默认地址：`http://127.0.0.1:5000`

## 3. 小程序端使用

1. 打开微信开发者工具，导入 `miniprogram/`
2. 打开 `miniprogram/utils/config.js`，把 `BASE_URL` 改为你的后端地址
3. 编译运行

## 4. Web 前端使用（本地）

### 4.1 启动后端

```bash
cd /Users/hh/Documents/work/miniapp/backend
python app.py
```

### 4.2 打开 Web 前端

直接用任意静态服务器打开 `web-frontend/` 即可。

例如：

```bash
cd /Users/hh/Documents/work/miniapp/web-frontend
python3 -m http.server 8080
```

浏览器访问 `http://127.0.0.1:8080`

说明：

- 面试页：`http://127.0.0.1:8080/index.html`
- 管理页：`http://127.0.0.1:8080/admin.html`

Web 前端默认请求 `/api/*`，容器化部署时由 Nginx 反向代理到 Flask。

## 5. Docker 容器部署（Linux 推荐）

项目根目录已提供：

- `backend/Dockerfile`
- `web-frontend/Dockerfile`
- `web-frontend/nginx.conf`
- `docker-compose.yml`

### 5.1 启动

```bash
cd /path/to/miniapp
docker compose up -d --build
```

### 5.2 访问

- Web 前端：`http://服务器IP:8080`
- 后端接口：`http://服务器IP:5000`

### 5.3 可选：接入大模型

在启动前设置环境变量（或写入服务器 shell 配置）：

```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY=你的key
docker compose up -d --build
```

或直接在 `backend/.env` 中配置（`docker-compose.yml` 已通过 `env_file` 自动加载该文件）。

调试时可以看接口返回字段：

- `engine=llm`：说明已调用模型
- `engine=fallback`：说明触发兜底规则
- `llm_error`：模型调用失败原因

## 6. API 概览

### GET `/get_questions?role=店铺运营`

返回该岗位已保存的固定题目。

返回字段包含：

- `engine`: 固定为 `store`
- `updated_at`: 该岗位题库最后更新时间

### POST `/submit_answers`

请求体：

```json
{
  "role": "店铺运营",
  "answers": [
    { "question_id": "strengths", "answer": "..." }
  ]
}
```

返回每题分数 + 平均分 + 岗位适配度。

### POST `/get_feedback`

请求体同上，返回每题改进建议。

### GET `/admin/questions?role=店铺运营`

获取后台已保存题目（管理页读取用）。

### POST `/admin/generate_questions`

请求体：

```json
{
  "role": "店铺运营",
  "count": 6
}
```

调用 AI 生成候选题目（不自动保存），返回 `engine`、`llm_provider`、`llm_error`。

### POST `/admin/save_questions`

请求体：

```json
{
  "role": "店铺运营",
  "questions": [
    { "id": "q1", "text": "请介绍你的优点和缺点。" }
  ]
}
```

保存编辑后的题目，保存后用户端立即按该内容展示。
