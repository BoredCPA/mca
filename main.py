from fastapi import FastAPI
from app.routes import merchant
from app.database import init_db

app = FastAPI()

init_db()  # 👈 create tables

app.include_router(merchant.router)
