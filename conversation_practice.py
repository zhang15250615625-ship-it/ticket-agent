# 在循环开始前创建列表，只创建一次
messages = [
    {"role": "system", "content": "你是工单助手。"}
]

while True:
    user_question = input("你：").strip()

    if user_question == "退出":
        print("对话结束")
        break

    if user_question == "":
        print("请输入内容")
        continue

    messages.append({
        "role": "user",
        "content": user_question
    })

    print("当前保存的消息：")
    for message in messages:
        print(message)