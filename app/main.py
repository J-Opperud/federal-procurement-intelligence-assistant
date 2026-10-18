from fastapi import FastAPI

from app.routers import system

app = FastAPI(
    title="Sentinel Scout API",
    description="Federal procurement intelligence and research API.",
    version="0.1.0",
)

app.include_router(system.router)
