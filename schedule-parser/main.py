from contextlib import asynccontextmanager
import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.web.exception_handler.exception_handler import register_exception_handlers
from app.web.router.scheduler_parser_routes import schedule_parser_router
from dependencies import get_logger_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.include_router(schedule_parser_router)
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

register_exception_handlers(app, get_logger_service().logger)

if __name__ == "__main__":
    # PARSER_HOST/PARSER_PORT позволяют запускать парсер локально
    # (127.0.0.1) без изменения кода; значения по умолчанию — серверные
    uvicorn.run("main:app",
                host=os.environ.get("PARSER_HOST", "192.168.2.250"),
                port=int(os.environ.get("PARSER_PORT", "8001")),
                reload=True)
