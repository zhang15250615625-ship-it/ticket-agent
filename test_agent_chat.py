"""连续对话的离线测试：所有网络请求均被模拟，不读取密钥。"""

import contextlib
import copy
import io
import json
import unittest
from unittest.mock import call, patch

import requests

import agent_chat


def model_response(message):
    response = requests.Response()
    response.status_code = 200
    response.encoding = "utf-8"
    response._content = json.dumps({"choices": [{"message": message}]}).encode("utf-8")
    return response


def text_response(content):
    return model_response({"role": "assistant", "content": content})


def tool_response(*ticket_ids):
    return model_response({
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": f"call_{index}",
                "type": "function",
                "function": {
                    "name": "get_ticket",
                    "arguments": json.dumps({"ticket_id": ticket_id}),
                },
            }
            for index, ticket_id in enumerate(ticket_ids)
        ],
    })


def create_response(title="键盘无法输入", description="连接电脑后按键没有反应"):
    return model_response({
        "role": "assistant", "content": None,
        "tool_calls": [{
            "id": "call_create", "type": "function",
            "function": {"name": "create_ticket", "arguments": json.dumps({
                "title": title, "description": description,
            })},
        }],
    })


class ConversationTests(unittest.TestCase):
    def run_chat(self, inputs, responses):
        sent_payloads = []
        response_iterator = iter(responses)
        output = io.StringIO()

        def fake_post(*args, **kwargs):
            sent_payloads.append(copy.deepcopy(kwargs["json"]))
            response = next(response_iterator)
            if isinstance(response, Exception):
                raise response
            return response

        with (
            patch.object(agent_chat, "load_dotenv"),
            patch.dict(agent_chat.os.environ, {"DASHSCOPE_API_KEY": "test-placeholder"}),
            patch("builtins.input", side_effect=inputs),
            patch.object(agent_chat.requests, "post", side_effect=fake_post),
            patch.object(agent_chat, "get_ticket", return_value={"status": "待处理"}) as query,
            patch.object(agent_chat, "create_ticket", return_value={
                "id": 3, "title": "键盘无法输入", "description": "连接电脑后按键没有反应",
                "status": "待处理",
            }) as create,
            contextlib.redirect_stdout(output),
        ):
            agent_chat.main()
        self.create_mock = create
        return sent_payloads, output.getvalue(), query

    def test_clarification_and_two_queries_keep_history(self):
        payloads, output, query = self.run_chat(
            ["帮我查一下工单", "1号", "再查2号", "退出"],
            [text_response("请提供工单编号。"), tool_response(1),
             text_response("1号待处理"), tool_response(2), text_response("2号待处理")],
        )
        self.assertEqual([p["tool_choice"] for p in payloads],
                         ["auto", "auto", "none", "auto", "none"])
        history = payloads[1]["messages"]
        self.assertEqual([m["role"] for m in history],
                         ["system", "user", "assistant", "user"])
        self.assertEqual(history[2]["content"], "请提供工单编号。")
        self.assertEqual(history[3]["content"], "1号")
        self.assertEqual(payloads[3]["messages"][-2]["content"], "1号待处理")
        self.assertEqual(payloads[2]["messages"][-1]["tool_call_id"], "call_0")
        self.assertEqual(query.call_args_list, [call(1), call(2)])
        self.assertIn("2号待处理", output)

    def test_failed_second_request_keeps_tool_results(self):
        bad_json = requests.Response()
        bad_json.status_code = 200
        bad_json._content = b"not json"
        server_error = requests.Response()
        server_error.status_code = 500
        server_error._content = b"{}"
        for failure in [requests.Timeout(), requests.ConnectionError(), server_error, bad_json]:
            with self.subTest(failure=type(failure).__name__):
                payloads, output, query = self.run_chat(
                    ["查工单", "1号", "重试查1号", "退出"],
                    [text_response("请提供编号"), tool_response(1), failure,
                     tool_response(1), text_response("1号待处理")],
                )
                self.assertEqual([m["role"] for m in payloads[3]["messages"]],
                                 ["system", "user", "assistant", "user", "assistant",
                                  "tool", "assistant", "user"])
                self.assertEqual(payloads[3]["messages"][-1]["content"], "重试查1号")
                self.assertEqual(payloads[3]["tool_choice"], "auto")
                self.assertEqual(query.call_count, 2)
                self.assertIn("本轮工具结果已保存", output)
                self.assertIn("1号待处理", output)

    def test_first_request_timeout_allows_retry(self):
        payloads, output, _ = self.run_chat(
            ["你好", "你好", "退出"], [requests.Timeout(), text_response("你好")]
        )
        self.assertEqual([m["role"] for m in payloads[1]["messages"]], ["system", "user"])
        self.assertIn("模型调用超时", output)
        self.assertIn("助手： 你好", output)

    def test_invalid_arguments_do_not_leave_incomplete_tool_calls(self):
        invalid = model_response({
            "role": "assistant", "content": None,
            "tool_calls": [{"id": "bad", "type": "function", "function": {
                "name": "get_ticket", "arguments": "not json"}}],
        })
        payloads, output, query = self.run_chat(
            ["查询1号", "你好", "退出"],
            [invalid, text_response("工具参数有误"), text_response("你好")]
        )
        self.assertEqual([m["role"] for m in payloads[2]["messages"]],
                         ["system", "user", "assistant", "tool", "assistant", "user"])
        self.assertIn("工具参数格式错误", payloads[1]["messages"][-1]["content"])
        query.assert_not_called()
        self.assertIn("工具参数格式错误", output)

    def test_every_tool_call_gets_a_matching_result(self):
        payloads, _, query = self.run_chat(
            ["查1号和2号", "退出"], [tool_response(1, 2), text_response("两张工单均待处理")]
        )
        results = [m for m in payloads[1]["messages"] if m["role"] == "tool"]
        self.assertEqual([m["tool_call_id"] for m in results], ["call_0", "call_1"])
        self.assertEqual(query.call_args_list, [call(1), call(2)])

    def test_invalid_ticket_id_is_not_executed(self):
        payloads, _, query = self.run_chat(
            ["查询0号", "退出"], [tool_response(0), text_response("编号必须是正整数")]
        )
        query.assert_not_called()
        self.assertEqual(json.loads(payloads[1]["messages"][-1]["content"]),
                         {"error": "工单编号必须是正整数"})

    def test_blank_input_and_exit_do_not_call_model(self):
        payloads, output, query = self.run_chat(["  ", "退出"], [])
        self.assertEqual(payloads, [])
        query.assert_not_called()
        self.assertIn("请输入内容", output)
        self.assertIn("对话结束", output)

    def test_create_requires_confirmation_then_can_be_queried(self):
        payloads, output, query = self.run_chat(
            ["新建工单", "确认", "查3号", "退出"],
            [create_response(" 键盘无法输入 ", " 连接电脑后按键没有反应 "),
             text_response("已创建3号工单"), tool_response(3), text_response("3号待处理")],
        )
        self.create_mock.assert_called_once_with("键盘无法输入", "连接电脑后按键没有反应")
        query.assert_called_once_with(3)
        self.assertEqual({t["function"]["name"] for t in payloads[0]["tools"]},
                         {"get_ticket", "create_ticket"})
        self.assertEqual(json.loads(payloads[1]["messages"][-1]["content"])["id"], 3)
        self.assertIn("即将创建工单", output)

    def test_cancel_or_other_text_never_creates(self):
        for confirmation in ["取消", "", "是", "退出"]:
            with self.subTest(confirmation=confirmation):
                payloads, _, query = self.run_chat(
                    ["新建工单", confirmation, "退出"],
                    [create_response(), text_response("已取消")],
                )
                self.create_mock.assert_not_called()
                query.assert_not_called()
                result = json.loads(payloads[1]["messages"][-1]["content"])
                self.assertTrue(result["cancelled"])
                self.assertNotIn("id", result)

    def test_invalid_creation_fields_do_not_prompt_or_create(self):
        for title, description in [(" ", "描述"), ("标题", ""), (None, "描述"), ("标题", 123)]:
            with self.subTest(title=title, description=description):
                payloads, output, _ = self.run_chat(
                    ["新建工单", "退出"],
                    [create_response(title, description), text_response("请补充内容")],
                )
                self.create_mock.assert_not_called()
                self.assertNotIn("即将创建工单", output)
                self.assertIn("error", json.loads(payloads[1]["messages"][-1]["content"]))

    def test_creation_result_survives_final_model_timeout(self):
        payloads, output, _ = self.run_chat(
            ["新建工单", "确认", "刚才创建的编号是什么", "退出"],
            [create_response(), requests.Timeout(), text_response("刚才创建的编号为3")],
        )
        self.create_mock.assert_called_once()
        history = payloads[2]["messages"]
        results = [json.loads(m["content"]) for m in history if m["role"] == "tool"]
        self.assertEqual(results[0]["id"], 3)
        self.assertIn("本轮工具结果已保存", history[-2]["content"])
        self.assertIn("刚才创建的编号为3", output)

    def test_malformed_later_call_prevents_partial_creation(self):
        message = create_response().json()["choices"][0]["message"]
        message["tool_calls"].append({"function": {"name": "get_ticket", "arguments": "{}"}})
        payloads, output, query = self.run_chat(
            ["新建并查询", "退出"], [model_response(message)]
        )
        self.create_mock.assert_not_called()
        query.assert_not_called()
        self.assertEqual(len(payloads), 1)
        self.assertIn("本轮未执行工具", output)


if __name__ == "__main__":
    unittest.main()
