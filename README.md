# Ticket Agent — 工单查询助手

使用 Python、FastAPI 和通义千问 API 实现的 Agent 学习项目。用户在终端输入自然语言问题，模型选择查询工具并提取工单编号，Python 查询本地工单接口，再将真实结果交给模型生成回答。

## 已实现功能

- FastAPI 工单列表、按编号查询、创建工单，以及输入校验。
- 使用 `requests` 调用千问，读取模型回答和 Token 用量。
- 为模型提供 `get_ticket` 工具说明，解析工具名称和 JSON 参数。
- 仅执行已登记的查询函数，并检查工单编号是否为正整数。
- 将工单数据以 `tool` 消息回传模型，生成最终回答。
- 对工单不存在的情况返回明确结果；通过提示词要求模型在缺少编号时询问用户。

## 查询流程

1. 用户输入：`帮我查一下1号工单的当前状态`。
2. 模型返回调用请求：`get_ticket(ticket_id=1)`。
3. Python 请求本地接口：`GET /tickets/1`。
4. 程序把查询结果加入对话，并通过 `tool_call_id` 对应到本次工具调用。
5. 第二次模型请求使用 `tool_choice="none"`，根据已有结果组织回答。

模型提出函数调用请求，具体函数由本地 Python 程序执行。

## 环境准备

已在 Windows、Python 3.10.10 下运行验证。以下命令用于 PowerShell，每条分别执行。首次下载项目：

```powershell
git clone https://github.com/zhang15250615625-ship-it/ticket-agent.git
cd ticket-agent
```

在项目根目录创建虚拟环境并安装依赖：

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

已有本项目虚拟环境时，不需要再次创建。

## 配置模型密钥

首次下载项目时，复制配置示例。已有 `.env` 时跳过复制，以免覆盖本地配置。

```powershell
Copy-Item .env.example .env
```

在本地 `.env` 中填写北京地域的百炼 API Key：

```dotenv
DASHSCOPE_API_KEY=在本地填写你的密钥
LLM_MODEL=qwen3.7-flash
```

`.env` 已通过 `.gitignore` 排除。GitHub 中只保留不含密钥的 `.env.example`。

## 运行工单查询 Agent

### 终端一：启动工单服务

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

保持这个终端运行。接口文档：<http://127.0.0.1:8000/docs>。

### 终端二：启动 Agent

打开另一个终端，进入同一项目根目录后执行：

```powershell
.\.venv\Scripts\python.exe agent_demo.py
```

输入示例：

```text
请输入你的问题：帮我查一下1号工单的当前状态
```

程序会打印模型选择的工具、实际查询结果和最终回答。编号 1 的初始工单标题为“耳机无法连接”，状态为“待处理”。

每次运行处理一个问题。需要工具时调用模型两次，直接回答时调用一次；深度思考已关闭，每次模型请求的最大输出为 512 tokens。费用以百炼实际计费为准。

## 已完成的手工验证

以下场景已在本地运行并观察到相应结果，模型回答的具体措辞可能不同。

| 场景 | 观察到的行为 |
| --- | --- |
| 查询 1 号工单 | 调用 `get_ticket(1)`，根据真实结果回答“待处理” |
| 查询 999 号工单 | 工具返回“工单不存在”，模型明确说明未找到该工单 |
| 输入“帮我查一下工单” | 模型询问工单编号，本轮没有调用工具 |

## 其他学习脚本

只练习模型 API 调用，不需要启动工单服务：

```powershell
.\.venv\Scripts\python.exe llm_demo.py
```

启动工单服务后，可以单独测试查询函数，或获取工单列表：

```powershell
.\.venv\Scripts\python.exe ticket_tools.py
.\.venv\Scripts\python.exe client.py
```

## 文件说明

| 文件 | 用途 |
| --- | --- |
| `main.py` | FastAPI 工单服务 |
| `client.py` | 请求本地工单列表 |
| `llm_demo.py` | 向千问发起一次对话请求 |
| `ticket_tools.py` | 封装按编号查询工单的函数，处理 404 情况 |
| `agent_demo.py` | 接收终端问题，完成模型选择工具、执行查询、回传结果和最终回答 |
| `.env.example` | 可公开的空配置示例 |
| `requirements.txt` | 当前项目使用的直接依赖版本 |

## 当前范围

- 工单保存在内存中，服务重启后恢复为初始数据。
- 当前 Agent 只查询工单；创建工单已有 HTTP 接口，尚未注册为模型工具。
- 每次运行的对话独立。模型追问编号后，需要重新运行并输入完整问题，目前没有多轮会话记忆。
- 已有基础参数检查；工具参数解析、工单服务连接和第二次模型请求的异常处理仍需完善。

## 下一步

1. 完善异常处理，覆盖服务未启动、连接超时、模型参数格式错误等情况。
2. 加入多轮会话，让用户能接着回答模型的追问。
3. 接入创建工单工具，并在写入前要求用户确认。
4. 增加工具调用数量限制、自动化功能测试和持久化存储。

## 参考

- [百炼兼容接口与北京地域地址](https://help.aliyun.com/zh/model-studio/compatibility-of-openai-with-dashscope)
- [千问深度思考参数](https://help.aliyun.com/zh/model-studio/deep-thinking)
- [千问 Function Calling](https://help.aliyun.com/zh/model-studio/qwen-function-calling)
- [python-dotenv 配置加载](https://bbc2.github.io/python-dotenv/)
