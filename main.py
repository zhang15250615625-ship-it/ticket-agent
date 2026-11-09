from pydantic import BaseModel
from fastapi import FastAPI, HTTPException

class TicketCreate(BaseModel):
    title: str
    description: str

app = FastAPI()

tickets = [
    {
        "id": 1,
        "title": "耳机无法连接",
        "status": "待处理"
    },
    {
        "id": 2,
        "title": "查询物流",
        "status": "已完成"
    }
]



@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/hello")
def say_hello():
    return {"message": "你好，这是我的第二个接口"}

@app.get("/tickets")
def list_tickets():
    return tickets

@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: int):
    for ticket in tickets:
        if ticket["id"] == ticket_id:
            return ticket

    raise HTTPException(
        status_code=404,
        detail="没有找到这张工单"
    )

@app.post("/tickets", status_code=201)
def create_ticket(data: TicketCreate):
    title = data.title.strip()
    if title == "":
        raise HTTPException(
            status_code=422,
            detail="标题不能为空"
        )
    description = data.description.strip()
    if description == "":
        raise HTTPException(
            status_code=422,
            detail="描述不能为空"
        )
    ticket = {
        "id": len(tickets) + 1,
        "title": title,
        "description": description,
        "status": "待处理"
    }

    tickets.append(ticket)
    return ticket