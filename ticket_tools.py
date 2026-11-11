import requests


def get_ticket(ticket_id: int):
    response = requests.get(
        f"http://127.0.0.1:8000/tickets/{ticket_id}",
        timeout=5
    )

    if response.status_code == 404:
        return {"error": "工单不存在", "ticket_id": ticket_id}

    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    print(get_ticket(1))
    print(get_ticket(999))