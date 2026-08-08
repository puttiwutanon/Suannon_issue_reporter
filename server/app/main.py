from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import CORS_ORIGINS
from .router import issues
from .router import reports
from . import webhook
from .scheduler import scheduler, start_scheduler

app = FastAPI(title="School Issue Reporter API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(issues.router)
app.include_router(reports.router)
app.include_router(webhook.router)


@app.on_event("startup")
def on_startup():
    start_scheduler()


@app.on_event("shutdown")
def shutdown_scheduler():
    scheduler.shutdown()
