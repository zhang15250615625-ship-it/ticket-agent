"""工单查询 Agent：由模型选择查询工具，再根据真实查询结果回答。"""

import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

from ticket_tools import get_ticket


def main():
    # 从当前代码文件旁边的 .env 加载配置，不受终端所在目录影响。
    load_dotenv(Path(__file__).resolve().parent / ".env")
    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("请先在本地 .env 的 DASHSCOPE_API_KEY= 后填入密钥并保存。")

    # headers 用来说明身份；密钥不直接写进 Python 代码。
    headers = {"Authorization": f"Bearer {api_key}"}

    user_question = input("请输入你的问题：").strip()

    if not user_question:
        print("问题不能为空")
        return

    # payload 就是发给模型的请求内容，形式仍然是 Python 字典。
    payload = {
        "model": os.getenv("LLM_MODEL", "qwen3.7-flash"),
        "messages": [
            {
                "role": "system",
                "content": "你是工单助手。查询工单信息时使用工具；缺少工单编号时先询问用户，不要猜测。"
            },
            {
                "role": "user",
                "content": user_question
            }
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "get_ticket",
                    "description": "根据工单编号查询工单详情和当前状态。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticket_id": {
                                "type": "integer",
                                "description": "要查询的工单编号"
                            }
                        },
                        "required": ["ticket_id"]
                    }
                }
            }
        ],
        "tool_choice": "auto",
        "enable_thinking": False,
        "max_tokens": 512,
    }

    # 与之前调用自己的 FastAPI 接口一样，这里也是发 HTTP 请求。
    try:
        response = requests.post(
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=(10, 60),
        )
    except requests.Timeout:
        raise SystemExit("调用超时，请稍后重试。")
    except requests.RequestException:
        raise SystemExit("请求未完成，请检查网络连接。")

    print("HTTP 状态码：", response.status_code)
    if not response.ok:
        # 打印报错方便排查，并隐藏响应中可能出现的密钥。
        print("服务返回：", response.text.replace(api_key, "[密钥已隐藏]"))
        raise SystemExit(1)

    try:
        result = response.json()
        answer = result["choices"][0]["message"]
    except (ValueError, KeyError, IndexError, TypeError):
        raise SystemExit("响应格式与预期不符，暂时无法读取模型回答。")

    print("模型返回的完整消息：")
    print(answer)
    tool_calls = answer.get("tool_calls") or []
    if not tool_calls:
        print("助手回答：", answer.get("content"))
        return

    payload["messages"].append(answer)

    for tool_call in tool_calls:
        function = tool_call["function"]

        if function["name"] != "get_ticket":
            print("不支持的工具：", function["name"])
            return

        arguments = json.loads(function["arguments"])
        ticket_id = arguments["ticket_id"]

        if type(ticket_id) is not int or ticket_id < 1:
            print("工单编号必须是正整数")
            return

        print("准备查询工单：", ticket_id)
        ticket = get_ticket(ticket_id)
        print("实际查询结果：", ticket)
        payload["messages"].append({
            "role": "tool",
            "tool_call_id": tool_call["id"],
            "content": json.dumps(ticket, ensure_ascii=False)
        })
    print("Token 用量：", result.get("usage", {}))

    # 这一轮让模型根据已有查询结果生成回答。
    payload["tool_choice"] = "none"

    final_response = requests.post(
        "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=(10, 60),
    )

    final_response.raise_for_status()
    final_result = final_response.json()

    print("助手最终回答：")
    print(final_result["choices"][0]["message"]["content"])
    print("第二次调用 Token 用量：", final_result.get("usage", {}))


if __name__ == "__main__":
    main()
