import requests


def get_ticket(ticket_id: int):
    try:
        response = requests.get(
            f"http://127.0.0.1:8000/tickets/{ticket_id}",
            timeout=5
        )

        if response.status_code == 404:
            return {
                "error": "工单不存在",
                "ticket_id": ticket_id
            }

        response.raise_for_status()
        return response.json()

    except requests.Timeout:
        return {
            "error": "查询工单超时，请稍后重试",
            "ticket_id": ticket_id
        }

    except requests.ConnectionError:
        return {
            "error": "暂时无法连接工单服务，请确认服务已启动",
            "ticket_id": ticket_id
        }

    except requests.HTTPError:
        return {
            "error": "工单服务返回异常，请稍后重试",
            "ticket_id": ticket_id
        }

def create_ticket(title: str, description: str):
    data = {
        "title": title,
        "description": description
    }

    try:
        response = requests.post(
            "http://127.0.0.1:8000/tickets",
            json=data,
            timeout=5
        )
        response.raise_for_status()
        return response.json()

    except requests.Timeout:
        return {
            "error": "创建请求超时，暂时无法确认是否成功，请先查询工单列表"
        }

    except requests.ConnectionError:
        return {
            "error": "连接工单服务失败，暂时无法确认创建结果"
        }

    except requests.HTTPError:
        return {
            "error": "工单服务返回错误，请检查提交内容和服务状态"
        }

if __name__ == "__main__":
    created_ticket = create_ticket(
        "键盘无法输入",
        "连接电脑后，按键没有反应"
    )
    print("创建结果：", created_ticket)

    if "id" in created_ticket:
        ticket_id = created_ticket["id"]
        print("再次查询：", get_ticket(ticket_id))
