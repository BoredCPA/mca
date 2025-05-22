from fastapi import FastAPI
from app.routes import merchant

app = FastAPI()

app.include_router(merchant.router)
