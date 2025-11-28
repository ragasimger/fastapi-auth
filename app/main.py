from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from base.camelize import CamelAPIResponse, CamelCaseRequestMiddleware, to_camel
from base.openapi_config import SWAGGER_UI_PARAMETERS
from base.response import setup_exception_handlers

app = FastAPI()


app = FastAPI(
    title="FastAPI Authentication and Authorization",
    swagger_ui_parameters=SWAGGER_UI_PARAMETERS,
    default_response_class=CamelAPIResponse,
    version="0.1.0",
)


def camel_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    components = schema.get("components", {}).get("schemas", {})
    for name, defs in components.items():
        if "properties" in defs:
            defs["properties"] = {to_camel(k): v for k, v in defs["properties"].items()}
        if "required" in defs:
            defs["required"] = [to_camel(r) for r in defs["required"]]

    app.openapi_schema = schema
    return schema


app.openapi = camel_openapi
app.add_middleware(CamelCaseRequestMiddleware)
setup_exception_handlers(app)


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def main():
    return {"message": "Hello World"}


# if __name__ == "__main__":
#     import uvicorn

#     uvicorn.run(app, host="0.0.0.0", port=8000)
