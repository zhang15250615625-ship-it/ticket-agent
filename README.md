# Ticket Agent — 工单查询助手

使用 Python、FastAPI 和通义千问 API 实现的 Agent 学习项目。用户在终端输入自然语言问题，模型选择查询工具并提取工单编号，Python 查询本地工单接口，再将真实结果交给模型生成回答。

## 已实现功能

- FastAPI 工单列表、按编号查询、创建工单，以及输入校验。
- 使用 `requests` 调用千问，读取模型回答和 Token 用量。
- 为模型提供 `get_ticket` 工具说明，解析工具名称和 JSON 参数。
- 仅执行已登记的查询函数，并检查工单编号是否为正整数。
- 将工单数据以 `tool` 消息回传模型，生成最终回答。
- 对工单不存在的情况返回明确结果；通过提示词要求模型在缺少编号时询问用户。
- 捕获工单服务的连接错误、超时和 HTTP 错误，返回错误字典并交给模型说明暂时无法查询。
- `agent_chat.py` 支持同一次运行中的连续对话，保存用户、助手和工具消息，每轮重新允许工具选择。
- 连续对话版本统一处理两次模型请求的网络及响应格式错误；第一步请求失败时不保存本轮，工具已执行后则保留执行结果。
- 支持 `create_ticket` 工具，检查标题和描述，在终端显示待提交内容，仅输入“确认”才发出创建请求；其他输入取消。

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

### 连续对话版本

保持工单服务运行，在第二个终端运行：

```powershell
.\.venv\Scripts\python.exe agent_chat.py
```

依次输入以下内容，验证模型是否能接着上一轮追问查询：

```text
帮我查一下工单
1号
再查一下2号
退出
```

程序把本次运行中已完成的对话随每轮请求一起发送。助手追问、工具调用、工具结果和最终回答均会保存；退出后清空，不跨运行保存。每轮最多请求模型两次。历史消息会占用输入 Token，目前尚未增加历史长度限制。

创建工具的手工验证步骤：

1. 输入 `帮我创建一张工单，标题是鼠标失灵，描述是连接电脑后光标无法移动`。
2. 程序显示标题和描述后，在确认提示处输入 `取消`，验证本次没有提交。
3. 再次提出创建请求，在确认提示处输入 `确认`。每次确认提交都会新增工单。
4. 用工具实际返回的编号继续询问 `帮我查一下这个编号的工单`，核对标题、描述和状态。

确认由 Python 的终端输入控制。模型给出的工具参数不代表用户已经确认。即使创建后的模型回答失败，程序也会显示并保存工具结果；不会自动重新提交。HTTP 超时或连接错误可能使创建结果不确定，应先查看工单列表，再决定是否重试。

## 已完成的单轮手工验证

以下场景已在本地运行并观察到相应结果，模型回答的具体措辞可能不同。

| 场景 | 观察到的行为 |
| --- | --- |
| 查询 1 号工单 | 调用 `get_ticket(1)`，根据真实结果回答“待处理” |
| 查询 999 号工单 | 工具返回“工单不存在”，模型明确说明未找到该工单 |
| 输入“帮我查一下工单” | 模型询问工单编号，本轮没有调用工具 |
| 停止工单服务后查询 1 号工单 | 查询函数返回连接错误，模型说明无法连接服务，没有误判为工单不存在 |
| 恢复工单服务后运行查询函数测试 | 1 号工单正常返回，999 号工单仍返回“工单不存在” |
| 直接运行创建函数后按返回编号查询 | 创建与回查均返回同一张 3 号工单，标题为“键盘无法输入” |

## 连续对话离线验证

```powershell
.\.venv\Scripts\python.exe -m unittest test_agent_chat -v
```

测试模拟模型和工单工具，不读取 `.env`，不发送网络请求，不消耗模型 Token。覆盖追问后补充编号、下一轮重新选择工具、保存最终回答、多工具结果对应、请求失败后继续、异常参数、空输入退出、确认创建、取消不提交及创建结果在模型超时后保留。真实模型的连续对话和创建确认效果仍需按上面的输入序列手工验证。

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
| `ticket_tools.py` | 封装查询和创建函数，处理连接错误、超时和 HTTP 错误；底部手工测试会创建一张工单 |
| `agent_demo.py` | 接收终端问题，完成模型选择工具、执行查询、回传结果和最终回答 |
| `conversation_practice.py` | 练习输入循环和用户消息列表，不调用模型 |
| `agent_chat.py` | 连续对话版，查询工单、经终端确认后创建工单，保存历史并处理模型请求的错误 |
| `test_ticket_errors.py` | 模拟工单服务返回 500 的练习 |
| `test_agent_chat.py` | 不调用真实服务的连续对话自动化测试 |
| `.env.example` | 可公开的空配置示例 |
| `requirements.txt` | 当前项目使用的直接依赖版本 |

## 当前范围

- 工单保存在内存中，服务重启后恢复为初始数据。
- `agent_chat.py` 可查询和创建工单；`agent_demo.py` 仍是单轮查询练习。
- `agent_demo.py` 是单轮学习版本；`agent_chat.py` 保存同一次运行中的对话，尚无跨运行保存、历史裁剪或多用户会话隔离。
- 连续对话版本包含参数格式检查及两次模型请求的异常处理；尚无自动重试或每轮工具调用数量限制。
- 创建接口尚无幂等机制；确认针对本次终端输入生效，重复确认提交仍会创建多张工单。

## 下一步

1. 手工验证真实模型的连续对话与确认创建流程，理解消息保存与工具选择设置。
2. 练习根据工具名称分支执行，解释标题、描述从用户输入到 HTTP 请求的过程。
3. 增加工具调用数量限制、历史长度限制和持久化存储。

## 参考

- [百炼兼容接口与北京地域地址](https://help.aliyun.com/zh/model-studio/compatibility-of-openai-with-dashscope)
- [千问深度思考参数](https://help.aliyun.com/zh/model-studio/deep-thinking)
- [千问 Function Calling](https://help.aliyun.com/zh/model-studio/qwen-function-calling)
- [python-dotenv 配置加载](https://bbc2.github.io/python-dotenv/)
