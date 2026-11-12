"""连续对话练习：查询工单，以及经终端确认后创建工单。"""

import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

from ticket_tools import create_ticket, get_ticket


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_ticket",
            "description": "根据工单编号查询工单详情和当前状态。",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "integer", "description": "要查询的工单编号"}
                },
                "required": ["ticket_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_ticket",
            "description": "用户明确要求创建工单且标题、描述齐全时使用，程序会在提交前请求用户确认。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "工单标题"},
                    "description": {"type": "string", "description": "用户描述的具体问题"},
                },
                "required": ["title", "description"],
            },
        },
    },
]


def confirm_create_ticket(arguments):
    """本课重点：先展示真实参数，只有终端输入“确认”才提交。"""
    title = arguments.get("title")
    description = arguments.get("description")
    if not isinstance(title, str) or not isinstance(description, str):
        return {"error": "创建工单需要文字形式的标题和描述，请向用户补充询问"}

    title = title.strip()
    description = description.strip()
    if not title or not description:
        return {"error": "标题和描述不能为空，请向用户补充询问"}

    print("即将创建工单：")
    print("标题：", title)
    print("描述：", description)
    confirmation = input("输入“确认”提交，其他输入取消：").strip()

    if confirmation != "确认":
        return {"cancelled": True, "message": "用户已取消，本次未提交创建请求"}

    return create_ticket(title, description)


def execute_tool(function):
    """根据模型给出的工具名称，选择已经登记的 Python 函数。"""
    name = function["name"]
    if name not in ("get_ticket", "create_ticket"):
        return {"error": "不支持这个工具"}
    try:
        arguments = json.loads(function["arguments"])
        if not isinstance(arguments, dict):
            raise ValueError("参数必须是对象")
    except (ValueError, TypeError):
        return {"error": "工具参数格式错误，需要 JSON 对象"}

    try:
        if name == "get_ticket":
            ticket_id = arguments.get("ticket_id")
            if type(ticket_id) is not int or ticket_id < 1:
                return {"error": "工单编号必须是正整数"}
            print("准备查询工单：", ticket_id)
            return get_ticket(ticket_id)

        return confirm_create_ticket(arguments)
    except requests.RequestException:
        return {"error": "无法读取工单服务的返回内容；若已提交创建，请先查询列表确认结果"}


def request_model(payload, headers):
    """两次模型请求共用错误处理；失败时返回 None。"""
    try:
        response = requests.post(
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=(10, 60),
        )
        response.raise_for_status()
    except requests.Timeout:
        print("模型调用超时，请稍后重试。")
        return None
    except requests.HTTPError:
        print("模型服务返回了错误状态码，请检查服务配置或稍后重试。")
        return None
    except requests.RequestException:
        print("模型请求未完成，请检查网络连接。")
        return None

    try:
        result = response.json()
        answer = result["choices"][0]["message"]
        if not isinstance(answer, dict) or answer.get("role") != "assistant":
            raise ValueError("缺少助手消息")
        tool_calls = answer.get("tool_calls") or []
        if not isinstance(tool_calls, list):
            raise ValueError("工具调用格式不正确")
        if not tool_calls:
            content = answer.get("content")
            if not isinstance(content, str) or not content.strip():
                raise ValueError("缺少回答内容")
    except (ValueError, KeyError, IndexError, TypeError):
        print("模型响应格式异常，暂时无法读取回答。")
        return None

    print("Token 用量：", result.get("usage", {}))
    return answer


def main():
    load_dotenv(Path(__file__).resolve().parent / ".env")
    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if not api_key:
        print("请先在本地 .env 中填写 DASHSCOPE_API_KEY 并保存。")
        return

    headers = {"Authorization": f"Bearer {api_key}"}

    # 重点一：历史列表放在循环外，只在启动时创建一次。
    messages = [
        {
            "role": "system",
            "content": (
                "你是工单助手。根据本次对话理解用户补充的工单编号。"
                "查询工单信息时使用工具；缺少编号时先询问用户，不要猜测。"
                "用户明确要求创建工单且标题和描述齐全时使用 create_ticket；缺少内容先追问，不要虚构。"
                "创建工具由程序在终端请求用户确认，你不能代替用户确认。"
                "工具返回 cancelled=true 时说明用户取消，不能说创建成功。"
                "根据工具的真实结果回答；工具返回错误时如实说明。"
            ),
        }
    ]

    print("工单助手已启动，输入“退出”结束本次对话。")
    while True:
        user_question = input("你：").strip()
        if user_question == "退出":
            print("对话结束")
            break
        if not user_question:
            print("请输入内容")
            continue

        # 先在副本中处理这一轮；工具结果齐全后会保存，文字回复失败也保留执行记录。
        turn_messages = messages.copy()
        turn_messages.append({"role": "user", "content": user_question})

        payload = {
            "model": os.getenv("LLM_MODEL", "qwen3.7-flash"),
            "messages": turn_messages,
            "tools": TOOLS,
            # 重点二：每轮重新允许模型选择工具。
            "tool_choice": "auto",
            "enable_thinking": False,
            "max_tokens": 512,
        }

        answer = request_model(payload, headers)
        if answer is None:
            print("本轮未保存，可以重新输入。")
            continue

        # 重点三：助手的追问也要保存，下一轮才能接着回答。
        turn_messages.append(answer)
        tool_calls = answer.get("tool_calls") or []
        if not tool_calls:
            messages = turn_messages
            print("助手：", answer["content"])
            continue

        # 先检查整批调用的结构，避免执行到一半才发现后续记录不完整。
        try:
            call_ids = set()
            for tool_call in tool_calls:
                call_id = tool_call["id"]
                function = tool_call["function"]
                if not isinstance(call_id, str) or not call_id or call_id in call_ids:
                    raise ValueError("工具调用编号缺失或重复")
                if not isinstance(function["name"], str) or not isinstance(function["arguments"], str):
                    raise ValueError("工具名称或参数类型异常")
                call_ids.add(call_id)
        except (ValueError, KeyError, IndexError, TypeError):
            print("工具调用结构异常，本轮未执行工具，也未保存。")
            continue

        for tool_call in tool_calls:
            ticket = execute_tool(tool_call["function"])
            print("工具执行结果：", ticket)
            turn_messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": json.dumps(ticket, ensure_ascii=False),
            })

        # 本轮工具结果已经齐全，让模型直接组织回答。
        payload["tool_choice"] = "none"
        final_answer = request_model(payload, headers)
        if final_answer is None or final_answer.get("tool_calls"):
            # 写入可能已经成功，不能因模型回答失败丢掉结果或自动重新创建。
            final_answer = {
                "role": "assistant",
                "content": (
                    "本轮工具结果已保存，但模型暂时无法生成文字回复。"
                    "请查看上方执行结果；创建结果不确定时，请先查询工单列表，避免重复提交。"
                ),
            }

        # 最终回答也加入历史，下一轮请求会携带这些消息。
        turn_messages.append(final_answer)
        messages = turn_messages
        print("助手：", final_answer["content"])


if __name__ == "__main__":
    main()
