# app/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.api.bidding.connection_manager import manager
from app.api.bidding.services.auction_scheduler import auction_scheduler
from app.api.bidding.services.event_bus import bidding_event_subscriber
from app.api.main import api_router
from app.api.submissions.services.submissions import judge0_client
from app.core.arq_pool import close_arq_pool, get_arq_pool
from app.core.config import settings
from app.core.exception_handlers import (
    app_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.exceptions.base import AppException
from app.core.logging import setup_logging
from app.core.middleware import RequestIDMiddleware, RequestLoggingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup/shutdown of long-lived resources."""
    await judge0_client.init()
    await get_arq_pool()
    # Run the bidding auction recovery sweep and start the in-process
    # scheduler so auctions auto-finish even across process restarts.
    await auction_scheduler.start()
    if settings.BIDDING_REDIS_PUBSUB_ENABLED:
        await bidding_event_subscriber.start(
            on_event=lambda contest_id, payload: manager.broadcast_local(
                contest_id=contest_id,
                message=payload,
            )
        )
    yield
    if settings.BIDDING_REDIS_PUBSUB_ENABLED:
        await bidding_event_subscriber.stop()
    await auction_scheduler.stop()
    await judge0_client.close()
    await close_arq_pool()


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    setup_logging()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        root_path="/api",
        lifespan=lifespan,
    )

    # Register exception handlers
    # Order matters: more specific exceptions should be registered first
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Must be outermost (added last) so request.client is rewritten to the real
    # client IP before any rate-limiting dependency or logging reads it.
    # Trusting only 127.0.0.1 (nginx on same VM) prevents IP spoofing via
    # forged X-Forwarded-For headers from external clients.
    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="127.0.0.1")

    # Register routers
    app.include_router(api_router)

    return app


app = create_app()
