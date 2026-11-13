from contextlib import asynccontextmanager

from pydantic import BaseModel
from fastapi import FastAPI, HTTPException

from db_query import (
    create_ticket_in_db,
    get_ticket_from_db,
    init_db,
    list_tickets_from_db,
)


class TicketCreate(BaseModel):
    title: str
    description: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 接受请求之前先准备数据库，不清空已有工单。
    init_db()
    yield


app = FastAPI(lifespan=lifespan)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/hello")
def say_hello():
    return {"message": "你好，这是我的第二个接口"}

@app.get("/tickets")
def list_tickets():
    return list_tickets_from_db()

@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: int):
    ticket = get_ticket_from_db(ticket_id)
    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="没有找到这张工单"
        )
    return ticket

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
    return create_ticket_in_db(title, description)
