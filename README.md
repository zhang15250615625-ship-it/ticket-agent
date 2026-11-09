# Ticket Agent 学习项目

从 Python 工单接口逐步学习大模型 API 和工具调用。

## 当前进度

- 已实现 FastAPI 工单列表、按 ID 查询、创建工单，以及输入校验。
- 已完成千问单次对话调用，并验证修改用户提问后能收到 HTTP 200 和新的模型回答。
- 尚未接入模型工具调用。目前模型不能操作工单。
- 工单数据保存在内存中，服务重启后会恢复为初始数据。

## 环境准备

使用 Python 3.10 或更高版本。以下命令用于 Windows PowerShell，每条分别执行。

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

已有本项目虚拟环境时，不需要再次创建。

## 运行模型调用练习

首次下载项目时，复制配置示例。已有 `.env` 时跳过复制，以免覆盖本地配置。

```powershell
Copy-Item .env.example .env
```

在本地 `.env` 中填写北京地域的百炼 API Key：

```dotenv
DASHSCOPE_API_KEY=在本地填写你的密钥
LLM_MODEL=qwen3.7-flash
```

```powershell
.\.venv\Scripts\python.exe llm_demo.py
```

成功时会输出 HTTP 200、模型回答和 Token 用量。此练习直接请求百炼，不需要启动本地工单服务。脚本关闭深度思考，限制单次最大输出为 512 tokens；调用费用以百炼实际计费为准。

`.env` 已通过 `.gitignore` 排除。GitHub 中只保留不含密钥的 `.env.example`。

## 运行工单接口

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

访问 <http://127.0.0.1:8000/docs> 进行接口测试。在另一个终端可运行：

```powershell
.\.venv\Scripts\python.exe client.py
```

## 文件说明

| 文件 | 用途 |
| --- | --- |
| `main.py` | FastAPI 工单服务 |
| `client.py` | 请求本地工单列表 |
| `llm_demo.py` | 向千问发起一次对话请求 |
| `.env.example` | 可公开的空配置示例 |
| `requirements.txt` | 当前项目使用的直接依赖版本 |

## 下一步

1. 封装查询工单工具，接入模型工具调用。
2. 添加创建工单前的用户确认。
3. 增加工具调用次数限制、异常处理与功能测试。

## 参考

- [百炼兼容接口与北京地域地址](https://help.aliyun.com/zh/model-studio/compatibility-of-openai-with-dashscope)
- [千问深度思考参数](https://help.aliyun.com/zh/model-studio/deep-thinking)
- [python-dotenv 配置加载](https://bbc2.github.io/python-dotenv/)
