import requests
from unittest.mock import patch

from ticket_tools import get_ticket


# 制作一个模拟响应，状态码是 500
fake_response = requests.Response()
fake_response.status_code = 500

# 临时替换 requests.get，让它返回模拟响应
with patch("ticket_tools.requests.get", return_value=fake_response):
    result = get_ticket(1)

print("查询结果：", result)

# 检查实际结果是否符合预期
assert result["error"] == "工单服务返回异常，请稍后重试"
assert result["ticket_id"] == 1

print("500 错误处理测试通过")