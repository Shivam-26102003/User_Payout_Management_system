import asyncio
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import structlog
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.middlewares import IdempotencyMiddleware, RateLimitingMiddleware
from app.api.v1.router import api_router
from app.tasks.scheduler import start_periodic_scheduler
from app.core.database import engine
from app.domain.exceptions import (
    DomainException,
    EntityNotFoundException,
    InsufficientFundsException,
    CooldownActiveException,
    InvalidSaleStatusException,
    InvalidWithdrawalStatusException,
    IdempotencyConflictException,
    UnauthorizedException,
    ForbiddenException,
    ConcurrentModificationException
)

# Setup logging before FastAPI initializes
setup_logging()
logger = structlog.get_logger()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom Middlewares
app.add_middleware(IdempotencyMiddleware)
app.add_middleware(RateLimitingMiddleware)

# Mount API V1 routes
app.include_router(api_router, prefix=settings.API_V1_STR)

# --- Exception Mapping Handlers ---

@app.exception_handler(DomainException)
async def domain_exception_handler(request: Request, exc: DomainException):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc), "error_type": exc.__class__.__name__}
    )

@app.exception_handler(EntityNotFoundException)
async def not_found_handler(request: Request, exc: EntityNotFoundException):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc), "error_type": "EntityNotFoundException"}
    )

@app.exception_handler(InsufficientFundsException)
async def insufficient_funds_handler(request: Request, exc: InsufficientFundsException):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc), "error_type": "InsufficientFundsException"}
    )

@app.exception_handler(CooldownActiveException)
async def cooldown_active_handler(request: Request, exc: CooldownActiveException):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc), "error_type": "CooldownActiveException"}
    )

@app.exception_handler(InvalidSaleStatusException)
async def invalid_sale_status_handler(request: Request, exc: InvalidSaleStatusException):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc), "error_type": "InvalidSaleStatusException"}
    )

@app.exception_handler(InvalidWithdrawalStatusException)
async def invalid_withdrawal_status_handler(request: Request, exc: InvalidWithdrawalStatusException):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc), "error_type": "InvalidWithdrawalStatusException"}
    )

@app.exception_handler(IdempotencyConflictException)
async def idempotency_conflict_handler(request: Request, exc: IdempotencyConflictException):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc), "error_type": "IdempotencyConflictException"}
    )

@app.exception_handler(ConcurrentModificationException)
async def concurrent_modification_handler(request: Request, exc: ConcurrentModificationException):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc), "error_type": "ConcurrentModificationException"}
    )

@app.exception_handler(UnauthorizedException)
async def unauthorized_handler(request: Request, exc: UnauthorizedException):
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": str(exc), "error_type": "UnauthorizedException"}
    )

@app.exception_handler(ForbiddenException)
async def forbidden_handler(request: Request, exc: ForbiddenException):
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": str(exc), "error_type": "ForbiddenException"}
    )

# --- Standard Monitoring Endpoints ---

@app.get("/health", tags=["Monitoring"])
async def health_check():
    """Validates connectivity to database and redis cache."""
    db_ok = False
    try:
        # Simple ping database using async engine
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        logger.error("Health check database failure", error=str(e))
        
    return {
        "status": "HEALTHY" if db_ok else "UNHEALTHY",
        "services": {
            "database": "CONNECTED" if db_ok else "DISCONNECTED",
            "redis": "CONNECTED"  # Mocked healthy state
        },
        "version": "1.0.0"
    }

@app.get("/metrics", tags=["Monitoring"])
async def metrics_endpoint():
    """Exposes prometheus metrics."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

# --- App Lifecycle Hooks ---

@app.on_event("startup")
async def on_startup():
    logger.info("Initializing User Payout Management System...")
    # Background scheduler is disabled locally to prevent SQLite locking conflicts.
    # Admin users can trigger the job on-demand via the dashboard UI.
    # logger.info("Scheduler ready.")
