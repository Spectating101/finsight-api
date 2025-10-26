"""
FinSight API - Main Application
Production-ready financial data API with monetization
"""

import os
import structlog
import asyncpg
import redis.asyncio as redis
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from src.auth.api_keys import APIKeyManager
from src.billing.stripe_integration import StripeManager
from src.middleware.auth import AuthMiddleware
from src.middleware.rate_limiter import RateLimitMiddleware
from src.data_sources.sec_edgar import SECEdgarSource
from src.data_sources import register_source

logger = structlog.get_logger(__name__)

# Global instances
db_pool: asyncpg.Pool = None
redis_client: redis.Redis = None
api_key_manager: APIKeyManager = None
stripe_manager: StripeManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global db_pool, redis_client, api_key_manager, stripe_manager

    # Startup
    logger.info("Starting FinSight API", version="1.0.0")

    # Connect to database
    database_url = os.getenv("DATABASE_URL", "postgresql://localhost/finsight_production")
    db_pool = await asyncpg.create_pool(
        database_url,
        min_size=5,
        max_size=20,
        command_timeout=60
    )
    logger.info("Database pool created")

    # Connect to Redis
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_client = await redis.from_url(
        redis_url,
        decode_responses=True,
        ssl_cert_reqs="none"  # Required for Heroku Redis TLS
    )
    logger.info("Redis connected")

    # Initialize managers
    api_key_manager = APIKeyManager(db_pool)
    stripe_manager = StripeManager(
        api_key=os.getenv("STRIPE_SECRET_KEY", ""),
        webhook_secret=os.getenv("STRIPE_WEBHOOK_SECRET", ""),
        db_pool=db_pool
    )
    logger.info("Managers initialized")

    # Register data sources
    sec_source = SECEdgarSource({
        "user_agent": os.getenv("SEC_USER_AGENT", "FinSight API/1.0 (contact@finsight.io)")
    })
    register_source(sec_source)
    logger.info("Data sources registered", sources=["SEC_EDGAR"])

    yield

    # Shutdown
    logger.info("Shutting down FinSight API")

    if db_pool:
        await db_pool.close()
    if redis_client:
        await redis_client.close()


# Create FastAPI app
app = FastAPI(
    title="FinSight API",
    description="Production-grade financial data API with AI-powered synthesis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"]
)

# Add authentication middleware
@app.on_event("startup")
async def startup_middleware():
    """Add middleware after startup (needs initialized managers)"""
    # Wait for lifespan startup to complete
    pass


# Note: Middleware is added after startup in the route setup below

# Add Prometheus metrics
Instrumentator().instrument(app).expose(app, include_in_schema=False)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(
        "Unhandled exception",
        exception=str(exc),
        path=request.url.path,
        method=request.method,
        exc_info=True
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An internal server error occurred",
            "request_id": getattr(request.state, "request_id", "unknown")
        }
    )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "FinSight API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "pricing": "https://finsight.io/pricing"
    }


# Health check
@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        # Check database
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")

        # Check Redis
        await redis_client.ping()

        return {
            "status": "healthy",
            "database": "ok",
            "redis": "ok",
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )


# Import and include routers
from src.api import metrics, auth, companies, subscriptions

# Set dependencies for auth and subscriptions routes
@app.on_event("startup")
async def setup_route_dependencies():
    """Setup route dependencies and middleware after managers are initialized"""
    # Wait a bit for lifespan to complete
    import asyncio
    await asyncio.sleep(0.1)

    # Inject dependencies into route modules
    from src.api import auth as auth_module
    from src.api import subscriptions as subs_module

    auth_module.set_dependencies(api_key_manager, db_pool)
    subs_module.set_dependencies(stripe_manager)

    # Add authentication and rate limiting middleware
    # Note: These must be added after lifespan startup completes
    from src.middleware import AuthMiddleware, RateLimitMiddleware

    app.add_middleware(RateLimitMiddleware, redis_client=redis_client)
    app.add_middleware(AuthMiddleware, api_key_manager=api_key_manager)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(metrics.router, prefix="/api/v1", tags=["Financial Metrics"])
app.include_router(companies.router, prefix="/api/v1", tags=["Companies"])
app.include_router(subscriptions.router, prefix="/api/v1", tags=["Billing"])


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    debug = os.getenv("DEBUG", "false").lower() == "true"

    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )
