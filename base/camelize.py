import json
import re
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware


class CamelAPIResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        # Pydantic model → plain dict (snake_case)
        if isinstance(content, BaseModel):
            content = content.model_dump(by_alias=False)

        def convert(v: Any) -> Any:
            if isinstance(v, dict):
                return {
                    to_camel(k): convert(vv)
                    for k, vv in v.items()
                    if not k.startswith("_")
                }
            if isinstance(v, list):
                return [convert(i) for i in v]
            return v

        camel = convert(content)
        return json.dumps(
            camel,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")


def to_camel(s: str) -> str:
    """Convert snake_case to camelCase"""
    parts = s.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def to_snake(s: str) -> str:
    """Convert camelCase to snake_case"""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", s).lower()


class CamelCaseRequestMiddleware(BaseHTTPMiddleware):
    """Middleware to convert incoming camelCase JSON to snake_case"""

    async def dispatch(self, request: Request, call_next):
        if request.method in {"POST", "PUT", "PATCH"} and request.headers.get(
            "content-type", ""
        ).startswith("application/json"):
            body = await request.body()
            if body:
                try:
                    raw = json.loads(body)

                    def convert(v: Any) -> Any:
                        if isinstance(v, dict):
                            return {to_snake(k): convert(vv) for k, vv in v.items()}
                        if isinstance(v, list):
                            return [convert(i) for i in v]
                        return v

                    snake = convert(raw)
                    request._body = json.dumps(snake).encode()
                except json.JSONDecodeError:
                    pass
        return await call_next(request)


def camelize_openapi_schema(schema: dict) -> dict:
    """
    Recursively convert all snake_case keys to camelCase in OpenAPI schema.
    This includes components, properties, required fields, parameters, and request/response bodies.
    """

    def camelize_object(obj: Any) -> Any:
        """Recursively camelize dictionary keys"""
        if isinstance(obj, dict):
            return {to_camel(k): camelize_object(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [camelize_object(item) for item in obj]
        else:
            return obj

    # Transform component schemas
    components = schema.get("components", {}).get("schemas", {})
    for name, definition in components.items():
        # Transform properties
        if "properties" in definition:
            definition["properties"] = {
                to_camel(prop): camelize_object(val)
                for prop, val in definition["properties"].items()
            }

        # Transform required fields
        if "required" in definition:
            definition["required"] = [to_camel(r) for r in definition["required"]]

    # Transform path parameters and request/response bodies
    for path, methods in schema.get("paths", {}).items():
        for method, details in methods.items():
            if method in ["get", "post", "put", "patch", "delete", "options", "head"]:
                # Transform parameters (query, path, header, cookie)
                if "parameters" in details:
                    for param in details["parameters"]:
                        if "name" in param:
                            param["name"] = to_camel(param["name"])

                # Transform request body schema references
                if "requestBody" in details:
                    request_body = details["requestBody"]
                    if "content" in request_body:
                        for content_type, content_details in request_body[
                            "content"
                        ].items():
                            if "schema" in content_details:
                                # Properties in inline schemas
                                if "properties" in content_details["schema"]:
                                    content_details["schema"]["properties"] = {
                                        to_camel(k): v
                                        for k, v in content_details["schema"][
                                            "properties"
                                        ].items()
                                    }
                                if "required" in content_details["schema"]:
                                    content_details["schema"]["required"] = [
                                        to_camel(r)
                                        for r in content_details["schema"]["required"]
                                    ]

                # Transform response body schema references
                if "responses" in details:
                    for status_code, response in details["responses"].items():
                        if "content" in response:
                            for content_type, content_details in response[
                                "content"
                            ].items():
                                if "schema" in content_details:
                                    # Properties in inline schemas
                                    if "properties" in content_details["schema"]:
                                        content_details["schema"]["properties"] = {
                                            to_camel(k): v
                                            for k, v in content_details["schema"][
                                                "properties"
                                            ].items()
                                        }
                                    if "required" in content_details["schema"]:
                                        content_details["schema"]["required"] = [
                                            to_camel(r)
                                            for r in content_details["schema"][
                                                "required"
                                            ]
                                        ]

    return schema
