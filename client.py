import requests

response = requests.get(
    "http://127.0.0.1:8000/tickets",
    timeout=5
)

print("状态码：", response.status_code)

tickets = response.json()
for i in tickets:
    print("返回数据：", i["title"])