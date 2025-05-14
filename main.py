from fastapi import FastAPI
from database import init_db
from routers import merchant

app = FastAPI()

init_db()

app.include_router(merchant.router)
