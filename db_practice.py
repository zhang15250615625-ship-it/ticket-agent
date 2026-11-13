import sqlite3
from pathlib import Path


# 把数据库文件放在当前 Python 文件旁边
db_path = Path(__file__).resolve().parent / "practice_tickets.db"

# 连接数据库；文件不存在时会创建
connection = sqlite3.connect(db_path)

# 创建工单表
connection.execute("""
    CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        status TEXT NOT NULL
    )
""")

# 写入一张工单
connection.execute(
    """
    INSERT INTO tickets (title, description, status)
    VALUES (?, ?, ?)
    """,
    ("鼠标失灵", "连接电脑后光标无法移动", "待处理")
)

# 提交写入操作
connection.commit()

# 查询全部工单，按编号排列
cursor = connection.execute(
    "SELECT id, title, description, status FROM tickets ORDER BY id"
)

# 取出查询结果
tickets = cursor.fetchall()

print("查询到的工单：")
for ticket in tickets:
    print(ticket)

connection.close()