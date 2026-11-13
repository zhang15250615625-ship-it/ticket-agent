"""真实 HTTP / SQLite 集成测试：使用临时数据库和独立端口，不调用模型。"""

import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

import requests


PROJECT_DIR = Path(__file__).resolve().parent


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="ticket-agent-test-")
        self.addCleanup(self.directory.cleanup)
        self.db_path = Path(self.directory.name) / "tickets.db"
        self.log_path = Path(self.directory.name) / "server.log"
        self.process = None
        self.log_file = None
        self.session = requests.Session()
        self.session.trust_env = False
        self.addCleanup(self.session.close)
        # 先停止自己启动的进程，再清理临时目录。
        self.addCleanup(self.stop_server)

    def start_server(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        self.base_url = f"http://127.0.0.1:{port}"
        environment = os.environ.copy()
        environment["TICKET_DB_PATH"] = str(self.db_path)
        environment["PYTHONUTF8"] = "1"
        self.log_file = self.log_path.open("ab")
        self.process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1",
             "--port", str(port), "--log-level", "warning", "--no-access-log"],
            cwd=PROJECT_DIR,
            env=environment,
            stdout=self.log_file,
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                break
            try:
                response = self.session.get(self.base_url + "/health", timeout=0.3)
                if response.status_code == 200:
                    return
            except requests.RequestException:
                pass
            time.sleep(0.05)
        self.stop_server()
        self.fail("Test server failed to start:\n" + self.log_path.read_text(encoding="utf-8"))

    def stop_server(self):
        if self.process is not None:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=5)
            self.process = None
        if self.log_file is not None:
            self.log_file.close()
            self.log_file = None

    def test_create_query_list_and_restart_persist_same_record(self):
        self.start_server()
        self.assertEqual(self.session.get(self.base_url + "/tickets", timeout=5).json(), [])
        response = self.session.post(self.base_url + "/tickets", json={
            "title": "  O'Reilly 的键盘  ", "description": "  重启后仍应保留这张工单  "
        }, timeout=5)
        self.assertEqual(response.status_code, 201)
        created = response.json()
        self.assertEqual(created["title"], "O'Reilly 的键盘")
        self.assertEqual(created["description"], "重启后仍应保留这张工单")
        self.assertEqual(created["status"], "待处理")
        ticket_id = created["id"]
        before = self.session.get(self.base_url + f"/tickets/{ticket_id}", timeout=5)
        self.assertEqual(before.status_code, 200)
        self.assertEqual(before.json(), created)

        # 真正结束服务进程，重新启动并读取同一个数据库文件。
        self.stop_server()
        self.start_server()
        after = self.session.get(self.base_url + f"/tickets/{ticket_id}", timeout=5)
        self.assertEqual(after.status_code, 200)
        self.assertEqual(after.json(), created)
        self.assertEqual(self.session.get(self.base_url + "/tickets", timeout=5).json(), [created])
        second = self.session.post(self.base_url + "/tickets", json={
            "title": "第二张工单", "description": "确认编号不会随重启重置"
        }, timeout=5)
        self.assertEqual(second.status_code, 201)
        self.assertGreater(second.json()["id"], ticket_id)

    def test_validation_and_missing_ticket_do_not_write_rows(self):
        self.start_server()
        missing = self.session.get(self.base_url + "/tickets/999", timeout=5)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json()["detail"], "没有找到这张工单")
        self.assertEqual(self.session.get(self.base_url + "/tickets/abc", timeout=5).status_code, 422)
        invalid_inputs = [
            {"title": "  ", "description": "描述"},
            {"title": "标题", "description": "  "},
            {"title": "缺少描述"},
        ]
        for data in invalid_inputs:
            with self.subTest(data=data):
                response = self.session.post(self.base_url + "/tickets", json=data, timeout=5)
                self.assertEqual(response.status_code, 422)
        self.assertEqual(self.session.get(self.base_url + "/tickets", timeout=5).json(), [])

    def test_startup_preserves_existing_database_contents(self):
        connection = sqlite3.connect(self.db_path)
        try:
            connection.execute("""
                CREATE TABLE tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL, description TEXT NOT NULL, status TEXT NOT NULL
                )
            """)
            connection.execute("INSERT INTO tickets VALUES (?, ?, ?, ?)",
                               (42, "原有工单", "此前已经保存", "已完成"))
            connection.commit()
        finally:
            connection.close()
        self.start_server()
        response = self.session.get(self.base_url + "/tickets/42", timeout=5)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "id": 42, "title": "原有工单", "description": "此前已经保存", "status": "已完成"
        })
        self.assertEqual(len(self.session.get(self.base_url + "/tickets", timeout=5).json()), 1)


if __name__ == "__main__":
    unittest.main()
