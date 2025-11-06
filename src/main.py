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
from src.middleware.security_headers import SecurityHeadersMiddleware
from src.data_sources.sec_edgar import SECEdgarSource
from src.data_sources import register_source
from src.utils.background_tasks import BackgroundTaskManager
from src import dependencies

# Initialize Sentry if configured
sentry_dsn = os.getenv("SENTRY_DSN")
if sentry_dsn:
    import sentry_sdk
    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=os.getenv("ENVIRONMENT", "production"),
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        profiles_sample_rate=float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1")),
    )

logger = structlog.get_logger(__name__)

# Global instances
db_pool: asyncpg.Pool = None
redis_client: redis.Redis = None
api_key_manager: APIKeyManager = None
stripe_manager: StripeManager = None
background_tasks: BackgroundTaskManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global db_pool, redis_client, api_key_manager, stripe_manager, background_tasks

    # Startup
    logger.info("Starting FinSight API", version="1.0.0")

    # Validate required environment variables
    required_vars = {
        "DATABASE_URL": "PostgreSQL database connection string",
        "REDIS_URL": "Redis connection string",
        "STRIPE_SECRET_KEY": "Stripe API secret key",
        "STRIPE_WEBHOOK_SECRET": "Stripe webhook signing secret",
        "SEC_USER_AGENT": "SEC EDGAR API user agent"
    }

    missing_vars = []
    invalid_vars = []

    for var, description in required_vars.items():
        value = os.getenv(var)
        if not value:
            missing_vars.append(f"{var} ({description})")
            continue

        # Validate format for specific variables
        if var == "STRIPE_SECRET_KEY" and not value.startswith("sk_"):
            invalid_vars.append(f"{var}: must start with 'sk_' (got: {value[:10]}...)")
        elif var == "STRIPE_WEBHOOK_SECRET" and not value.startswith("whsec_"):
            invalid_vars.append(f"{var}: must start with 'whsec_' (got: {value[:10]}...)")
        elif var == "DATABASE_URL" and not value.startswith("postgresql"):
            invalid_vars.append(f"{var}: must be a PostgreSQL URL (got: {value[:20]}...)")
        elif var == "REDIS_URL" and not (value.startswith("redis://") or value.startswith("rediss://")):
            invalid_vars.append(f"{var}: must be a Redis URL (got: {value[:20]}...)")

    if missing_vars:
        error_msg = f"Missing required environment variables:\n  " + "\n  ".join(missing_vars)
        logger.error(error_msg)
        raise ValueError(error_msg)

    if invalid_vars:
        error_msg = f"Invalid environment variable formats:\n  " + "\n  ".join(invalid_vars)
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.info("Environment variables validated successfully")

    # Connect to database
    database_url = os.getenv("DATABASE_URL")
    db_pool = await asyncpg.create_pool(
        database_url,
        min_size=5,
        max_size=20,
        command_timeout=60,
        timeout=30,  # Connection acquisition timeout (seconds)
        max_inactive_connection_lifetime=300  # Close idle connections after 5 minutes
    )
    logger.info("Database pool created", min_size=5, max_size=20)

    # Connect to Redis with proper TLS configuration
    redis_url = os.getenv("REDIS_URL")

    # Configure SSL/TLS for Redis
    import ssl
    ssl_context = None
    if redis_url.startswith("rediss://"):
        ssl_context = ssl.create_default_context()
        # Only skip verification if explicitly set (e.g., for Heroku Redis)
        if os.getenv("REDIS_TLS_SKIP_VERIFY", "false").lower() == "true":
            logger.warning("Redis TLS verification disabled - not recommended for production")
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

    redis_client = await redis.from_url(
        redis_url,
        decode_responses=True,
        ssl=ssl_context
    )
    logger.info("Redis connected", tls_enabled=redis_url.startswith("rediss://"))

    # Make Redis available to other modules
    dependencies.set_redis_client(redis_client)

    # Initialize managers
    api_key_manager = APIKeyManager(db_pool)
    stripe_manager = StripeManager(
        api_key=os.getenv("STRIPE_SECRET_KEY"),
        webhook_secret=os.getenv("STRIPE_WEBHOOK_SECRET"),
        db_pool=db_pool
    )
    logger.info("Managers initialized")

    # Register data sources
    sec_source = SECEdgarSource({
        "user_agent": os.getenv("SEC_USER_AGENT")
    })
    register_source(sec_source)
    logger.info("Data sources registered", sources=["SEC_EDGAR"])

    # Inject dependencies into route modules
    from src.api import auth as auth_module
    from src.api import subscriptions as subs_module
    from src.api import gdpr as gdpr_module

    auth_module.set_dependencies(api_key_manager, db_pool)
    subs_module.set_dependencies(stripe_manager, api_key_manager)
    gdpr_module.set_dependencies(db_pool)
    logger.info("Route dependencies injected")

    # Start background tasks (monthly usage reset, etc.)
    background_tasks = BackgroundTaskManager(db_pool)
    await background_tasks.start()
    logger.info("Background tasks started")

    yield

    # Shutdown
    logger.info("Shutting down FinSight API")

    if background_tasks:
        await background_tasks.stop()
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

# Add CORS middleware with production-safe defaults
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "*")
allowed_origins = allowed_origins_str.split(",") if allowed_origins_str != "*" else ["*"]

# Warn if using wildcard in production
if allowed_origins == ["*"]:
    logger.warning(
        "CORS wildcard (*) enabled - not recommended for production",
        recommendation="Set ALLOWED_ORIGINS environment variable to specific domains"
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "PUT", "PATCH"],
    allow_headers=["*"]
)

# Request ID tracking middleware (runs first)
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Add unique request ID to all requests for tracing"""
    import uuid

    # Get request ID from header or generate new one
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id

    # Process request
    response = await call_next(request)

    # Add request ID to response headers
    response.headers["X-Request-ID"] = request_id

    return response


# Authentication and rate limiting middleware
@app.middleware("http")
async def authentication_middleware(request: Request, call_next):
    """Apply authentication to all requests"""
    # Skip middleware if managers not initialized yet
    if api_key_manager is None:
        return await call_next(request)

    auth_mw = AuthMiddleware(app, api_key_manager)
    return await auth_mw.dispatch(request, call_next)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Apply rate limiting to all requests"""
    # Skip middleware if Redis not initialized yet
    if redis_client is None:
        return await call_next(request)

    rate_mw = RateLimitMiddleware(app, redis_client)
    return await rate_mw.dispatch(request, call_next)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Apply security headers to all responses"""
    sec_mw = SecurityHeadersMiddleware(app)
    return await sec_mw.dispatch(request, call_next)


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
    """Comprehensive health check endpoint"""
    health_status = {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }

    all_healthy = True

    try:
        # Check database
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        health_status["checks"]["database"] = f"error: {str(e)[:100]}"
        all_healthy = False

    try:
        # Check Redis
        await redis_client.ping()
        health_status["checks"]["redis"] = "ok"
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        health_status["checks"]["redis"] = f"error: {str(e)[:100]}"
        all_healthy = False

    # Check data sources
    try:
        from src.data_sources import get_registry
        registry = get_registry()
        source_health = await registry.health_check_all()

        health_status["checks"]["data_sources"] = {}
        for source_type, is_healthy in source_health.items():
            status = "ok" if is_healthy else "degraded"
            health_status["checks"]["data_sources"][source_type.value] = status
            if not is_healthy:
                all_healthy = False
    except Exception as e:
        logger.error("Data source health check failed", error=str(e))
        health_status["checks"]["data_sources"] = f"error: {str(e)[:100]}"
        all_healthy = False

    # Set overall status
    health_status["status"] = "healthy" if all_healthy else "degraded"

    # Return appropriate HTTP status code
    status_code = 200 if all_healthy else 503

    return JSONResponse(
        status_code=status_code,
        content=health_status
    )


# Import and include routers
from src.api import metrics, auth, companies, subscriptions, gdpr

# Note: Dependencies are injected during lifespan startup
# Middleware is added after lifespan completes via the lifespan context manager

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(metrics.router, prefix="/api/v1", tags=["Financial Metrics"])
app.include_router(companies.router, prefix="/api/v1", tags=["Companies"])
app.include_router(subscriptions.router, prefix="/api/v1", tags=["Billing"])
app.include_router(gdpr.router, prefix="/api/v1", tags=["GDPR Compliance"])


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
