from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import CORS_ORIGINS, CORS_ORIGIN_REGEX, limiter
from .router import issues, reports
from . import webhook
from .scheduler import scheduler, start_scheduler
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware

app = FastAPI(title="School Issue Reporter API")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  
app.add_middleware(SlowAPIMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=CORS_ORIGIN_REGEX,
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

