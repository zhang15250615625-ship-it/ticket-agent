# Ticket Agent — 工单查询助手

使用 Python、FastAPI、SQLite 和通义千问 API 实现的 Agent 学习项目。用户在终端输入自然语言问题，模型选择查询或创建工具，Python 调用本地工单接口，再将真实结果交给模型生成回答。创建前由终端请求用户确认，工单保存到数据库文件中。

## 已实现功能

- FastAPI 工单列表、按编号查询、创建工单，以及输入校验。
- 三个工单接口统一读写 SQLite；服务启动时准备表，重启后保留已提交的工单和编号。
- 使用 `requests` 调用千问，读取模型回答和 Token 用量。
- 为模型提供 `get_ticket` 工具说明，解析工具名称和 JSON 参数。
- 仅执行已登记的查询、创建函数，检查查询编号以及创建所需的标题和描述。
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

默认数据库是项目目录下的 `practice_tickets.db`，继续使用学习时写入的数据。首次下载项目并启动时会自动创建空表，不会自动插入示例工单；可在接口文档的 `POST /tickets` 中创建，或使用下面的连续对话 Agent 创建。接口读取的是数据库中的工单，先前内存列表中的临时记录不会自动导入。

数据库文件及事务文件已加入 `.gitignore`。自动化测试通过 `TICKET_DB_PATH` 指定独立的临时数据库；正常学习不需要设置此变量。

### 终端二：启动 Agent

打开另一个终端，进入同一项目根目录后执行：

```powershell
.\.venv\Scripts\python.exe agent_demo.py
```

输入示例：

```text
请输入你的问题：帮我查一下1号工单的当前状态
```

程序会打印模型选择的工具、实际查询结果和最终回答。请使用数据库中实际存在的编号；新数据库尚未创建工单时，查询 1 号会返回“工单不存在”。

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

## 学习过程中已完成的手工验证

以下场景已在本地运行并观察到相应结果，模型回答的具体措辞可能不同。表中的固定编号来自当时的测试数据；改用 SQLite 后以数据库中的实际记录为准。

| 场景 | 观察到的行为 |
| --- | --- |
| 查询 1 号工单 | 调用 `get_ticket(1)`，根据真实结果回答“待处理” |
| 查询 999 号工单 | 工具返回“工单不存在”，模型明确说明未找到该工单 |
| 输入“帮我查一下工单” | 模型询问工单编号，本轮没有调用工具 |
| 停止工单服务后查询 1 号工单 | 查询函数返回连接错误，模型说明无法连接服务，没有误判为工单不存在 |
| 恢复工单服务后运行查询函数测试 | 1 号工单正常返回，999 号工单仍返回“工单不存在” |
| 直接运行创建函数后按返回编号查询 | 创建与回查均返回同一张 3 号工单，标题为“键盘无法输入” |
| Agent 创建确认处输入“取消” | 工具返回 `cancelled: true`，助手说明本次创建已取消 |
| 接着询问“刚才创建的工单” | Agent 选择查询 3 号，返回“鼠标失灵”的工单内容 |
| SQLite 练习脚本连续运行两次 | 第二次查询仍有第一条记录，并增加第二条记录 |
| 数据库创建函数后按返回编号查询 | 创建与回查的编号、标题、描述和状态一致 |

## 连续对话离线验证

```powershell
.\.venv\Scripts\python.exe -m unittest test_agent_chat -v
```

测试模拟模型和工单工具，不读取 `.env`，不发送网络请求，不消耗模型 Token。覆盖追问后补充编号、下一轮重新选择工具、保存最终回答、多工具结果对应、请求失败后继续、异常参数、空输入退出、确认创建、取消不提交及创建结果在模型超时后保留。

## 数据库与接口集成验证

```powershell
.\.venv\Scripts\python.exe -m unittest test_persistence -v
```

测试在独立端口启动真实 Uvicorn 服务，使用临时数据库，不读取本地 `.env`，不调用模型。覆盖首次建表、创建后查询和列表一致、真正结束并重启服务后仍可查询、已有数据保留、编号继续增长、404 和 422，以及无效输入不写入数据。

手工验证步骤：

1. 保持服务运行，在 `agent_chat.py` 中确认创建一张工单，记下实际编号。
2. 在运行 Uvicorn 的终端按 `Ctrl+C`，然后重新执行原启动命令。
3. 再通过 Agent 查询刚才的编号，核对同一张工单的数据。

工单记录保存在数据库里。Agent 的聊天历史目前仍只保存在本次运行的内存中，重启 Agent 后需要重新提供工单编号。

## 其他学习脚本

只练习模型 API 调用，不需要启动工单服务：

```powershell
.\.venv\Scripts\python.exe llm_demo.py
```

启动工单服务后，运行工具函数练习或获取工单列表。注意：`ticket_tools.py` 的底部测试每运行一次会创建一张工单，再按返回编号查询。

```powershell
.\.venv\Scripts\python.exe ticket_tools.py
.\.venv\Scripts\python.exe client.py
```

SQLite 学习脚本可独立运行：`db_practice.py` 练习建表、插入与查询；`db_query.py` 提供可供接口调用的数据库函数，直接运行时会创建一张工单并回查。这两个脚本的写入练习每运行一次都会新增一条数据。

## 文件说明

| 文件 | 用途 |
| --- | --- |
| `main.py` | FastAPI 工单接口，启动时初始化表并调用数据库函数 |
| `db_query.py` | SQLite 初始化、列表、按编号查询及创建函数 |
| `db_practice.py` | 建表、写入与查询的独立学习脚本 |
| `client.py` | 请求本地工单列表 |
| `llm_demo.py` | 向千问发起一次对话请求 |
| `ticket_tools.py` | 封装查询和创建函数，处理连接错误、超时和 HTTP 错误；底部手工测试会创建一张工单 |
| `agent_demo.py` | 接收终端问题，完成模型选择工具、执行查询、回传结果和最终回答 |
| `conversation_practice.py` | 练习输入循环和用户消息列表，不调用模型 |
| `agent_chat.py` | 连续对话版，查询工单、经终端确认后创建工单，保存历史并处理模型请求的错误 |
| `test_ticket_errors.py` | 模拟工单服务返回 500 的练习 |
| `test_agent_chat.py` | 不调用真实服务的连续对话自动化测试 |
| `test_persistence.py` | 临时数据库上的真实 HTTP 及服务重启测试 |
| `.env.example` | 可公开的空配置示例 |
| `requirements.txt` | 当前项目使用的直接依赖版本 |

## 当前范围

- 工单保存到本地 SQLite 文件中，服务重启后保留；暂未做数据库备份和结构迁移工具。
- `agent_chat.py` 可查询和创建工单；`agent_demo.py` 仍是单轮查询练习。
- `agent_demo.py` 是单轮学习版本；`agent_chat.py` 保存同一次运行中的对话，尚无跨运行保存、历史裁剪或多用户会话隔离。
- 连续对话版本包含参数格式检查及两次模型请求的异常处理；尚无自动重试或每轮工具调用数量限制。
- 创建接口尚无幂等机制；确认针对本次终端输入生效，重复确认提交仍会创建多张工单。

## 下一步

1. 理解 Agent 工具、HTTP 接口、数据库函数之间的调用关系，完成重启后的回查练习。
2. 增加工具调用数量限制与历史长度限制，整理项目讲解和演示。
3. 开始知识库 RAG 项目。

## 参考

- [百炼兼容接口与北京地域地址](https://help.aliyun.com/zh/model-studio/compatibility-of-openai-with-dashscope)
- [千问深度思考参数](https://help.aliyun.com/zh/model-studio/deep-thinking)
- [千问 Function Calling](https://help.aliyun.com/zh/model-studio/qwen-function-calling)
- [python-dotenv 配置加载](https://bbc2.github.io/python-dotenv/)
- [Python 3.10 sqlite3](https://docs.python.org/3.10/library/sqlite3.html)
- [FastAPI 启动与关闭流程](https://fastapi.tiangolo.com/advanced/events/)
