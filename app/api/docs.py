from fastapi import FastAPI
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

from base.camelize import camelize_openapi_schema
from base.configs import settings


def v1_openapi(app: FastAPI) -> dict:
    if getattr(app, "openapi_schema", None) is not None:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        terms_of_service=app.terms_of_service,
        contact=app.contact,
        license_info=app.license_info,
        routes=app.routes,
        tags=app.openapi_tags,
        # servers=app.servers,
    )

    filtered_paths = {}
    for path, path_def in schema["paths"].items():
        if path.startswith(settings.API_V1_PREFIX):
            new_path = path[len(settings.API_V1_PREFIX) :] or "/"
            filtered_paths[new_path] = path_def
        elif path == "/health":
            filtered_paths[path] = path_def

    schema["paths"] = filtered_paths
    schema.setdefault("servers", []).insert(
        0,
        {
            "url": settings.API_V1_PREFIX,
        },
    )
    schema["info"]["title"] = f"{settings.APP_NAME} - API v1"

    app.openapi_schema = camelize_openapi_schema(schema)
    return schema


def get_v2_docs(app: FastAPI) -> None:
    @app.get("/api/v2/openapi.json", include_in_schema=False)
    def v2_openapi_json():
        schema = get_openapi(
            title=f"{settings.APP_NAME} - API v2",
            version="2.0.0",
            openapi_version=app.openapi_version,
            description=app.description,
            terms_of_service=app.terms_of_service,
            contact=app.contact,
            license_info=app.license_info,
            routes=app.routes,
            tags=app.openapi_tags,
            # servers=app.servers,
        )

        filtered_paths = {}
        for path, path_def in schema["paths"].items():
            if path.startswith("/api/v2"):
                new_path = path[len("/api/v2") :] or "/"
                filtered_paths[new_path] = path_def
            elif path == "/health":
                filtered_paths[path] = path_def

        schema["paths"] = filtered_paths
        schema.setdefault("servers", []).insert(
            0,
            {
                "url": settings.API_V2_PREFIX,
            },
        )

        return camelize_openapi_schema(schema)

    @app.get("/api/v2/docs", include_in_schema=False)
    async def v2_swagger_ui():
        return get_swagger_ui_html(
            openapi_url="/api/v2/openapi.json",
            title=f"{settings.APP_NAME} - API v2 - Swagger UI",
            swagger_ui_parameters={"defaultModelsExpandDepth": -1},
        )

    @app.get("/api/v2/redoc", include_in_schema=False)
    async def v2_redoc():
        return get_redoc_html(
            openapi_url="/api/v2/openapi.json",
            title=f"{settings.APP_NAME} - API v2 - ReDoc",
        )


def include_docs_routers(app: FastAPI) -> None:
    # if settings.DEBUG:
    #     pass
    default_docs = v1_openapi(app)
    app.openapi_schema = default_docs
    get_v2_docs(app)
