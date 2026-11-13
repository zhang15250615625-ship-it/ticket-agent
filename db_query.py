import os
import sqlite3
from pathlib import Path


# 默认继续使用练习数据库；自动化测试可指定一个独立的临时文件。
db_path = Path(os.getenv(
    "TICKET_DB_PATH",
    str(Path(__file__).resolve().parent / "practice_tickets.db")
)).expanduser().resolve()


def init_db():
    """启动服务时准备表；已有表和已有工单会保留。"""
    connection = sqlite3.connect(db_path)
    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL
            )
        """)
        connection.commit()
    finally:
        connection.close()


def list_tickets_from_db():
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        cursor = connection.execute(
            "SELECT id, title, description, status FROM tickets ORDER BY id"
        )
        return [dict(ticket) for ticket in cursor.fetchall()]
    finally:
        connection.close()


def get_ticket_from_db(ticket_id: int):
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row

    try:
        cursor = connection.execute(
            """
            SELECT id, title, description, status
            FROM tickets
            WHERE id = ?
            """,
            (ticket_id,)
        )

        ticket = cursor.fetchone()

        if ticket is None:
            return None

        return dict(ticket)

    finally:
        connection.close()


def create_ticket_in_db(title: str, description: str):
    status = "待处理"
    connection = sqlite3.connect(db_path)

    try:
        cursor = connection.execute(
            """
            INSERT INTO tickets (title, description, status)
            VALUES (?, ?, ?)
            """,
            (title, description, status)
        )

        connection.commit()

        # 获取数据库为这张新工单生成的编号
        ticket_id = cursor.lastrowid

        return {
            "id": ticket_id,
            "title": title,
            "description": description,
            "status": status
        }

    finally:
        connection.close()


if __name__ == "__main__":
    init_db()
    created_ticket = create_ticket_in_db(
        "显示器黑屏",
        "连接主机后，显示器没有画面"
    )
    print("创建结果：", created_ticket)

    ticket_id = created_ticket["id"]
    saved_ticket = get_ticket_from_db(ticket_id)
    print("数据库回查：", saved_ticket)
