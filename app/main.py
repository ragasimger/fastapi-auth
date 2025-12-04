import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.docs import include_docs_routers
from app.api.routers import api_router_v1, api_router_v2
from app.core.configs import SWAGGER_UI_PARAMETERS, init_logging, settings
from app.core.exception_handlers import (
    StarletteHTTPException,
    app_exception_handler,
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.core.exceptions import APIException
from base.camelize import (
    CamelCaseRequestMiddleware,
    camelize_openapi_schema,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logging.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    yield
    logging.info("Shutting down application")


def create_application() -> FastAPI:
    app = FastAPI(
        debug=settings.DEBUG,
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url=f"{settings.API_V1_PREFIX}/docs",
        redoc_url=f"{settings.API_V1_PREFIX}/redoc",
        swagger_ui_parameters=SWAGGER_UI_PARAMETERS,
        lifespan=lifespan,
    )
    # Cors
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # camelcase middleware
    app.add_middleware(CamelCaseRequestMiddleware)

    # exception handlers
    app.add_exception_handler(Exception, generic_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(APIException, app_exception_handler)

    # Routes
    app.include_router(api_router_v1, prefix=settings.API_V1_PREFIX)
    app.include_router(api_router_v2, prefix=settings.API_V2_PREFIX)

    return app


init_logging()
logger = logging.getLogger(__name__)
app = create_application()
include_docs_routers(app)


@app.get("/", include_in_schema=False)
async def home():
    return {
        "message": f"Welcome to the {settings.APP_NAME} API!",
        "docs": [
            {
                "version": "v1",
                "SwaggerURL": f"{settings.API_V1_PREFIX}/docs",
                "RedocURL": f"{settings.API_V1_PREFIX}/redoc",
            },
            {
                "version": "v2",
                "SwaggerURL": f"{settings.API_V2_PREFIX}/docs",
                "RedocURL": f"{settings.API_V2_PREFIX}/redoc",
            },
        ],
    }


@app.get("/health", tags=["System-Health"], include_in_schema=True)
async def health_check() -> dict[str, str]:
    """Health check endpoint for load balancers."""
    return {"status": "healthy"}
