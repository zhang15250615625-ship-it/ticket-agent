"""第一次模型调用练习：运行此文件，向千问提问一次。"""

import os
from pathlib import Path

import requests
from dotenv import load_dotenv


def main():
    # 从当前代码文件旁边的 .env 加载配置，不受终端所在目录影响。
    load_dotenv(Path(__file__).resolve().parent / ".env")
    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("请先在本地 .env 的 DASHSCOPE_API_KEY= 后填入密钥并保存。")

    # headers 用来说明身份；密钥不直接写进 Python 代码。
    headers = {"Authorization": f"Bearer {api_key}"}

    # payload 就是发给模型的请求内容，形式仍然是 Python 字典。
    payload = {
        "model": os.getenv("LLM_MODEL", "qwen3.7-flash"),
        "messages": [
            {"role": "system", "content": "你是一名耐心的 Python 老师，请用中文简洁回答。"},
            {"role": "user", "content": "请用工单系统举例，解释 GET 请求和 POST 请求的区别，控制在150字以内。"},
        ],
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
        answer = result["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError):
        raise SystemExit("响应格式与预期不符，暂时无法读取模型回答。")

    print("模型回答：")
    print(answer)
    print("Token 用量：", result.get("usage", {}))


if __name__ == "__main__":
    main()
