from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from app.routers import ask
from app.routers import auth, documents, research, system
from app.utils.exceptions import AppException
from app.utils.exception_handlers import (
    app_exception_handler,
    validation_exception_handler,
)

app = FastAPI(
    title="Sentinel Scout API",
    description="Federal procurement intelligence and research API.",
    version="0.1.0",
)

app.include_router(system.router)
app.include_router(auth.router)
app.include_router(research.router)
app.include_router(documents.router)
app.include_router(ask.router)

app.add_exception_handler(
    AppException,
    app_exception_handler,
)

app.add_exception_handler(
    RequestValidationError,
    validation_exception_handler,
)
