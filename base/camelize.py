import json
import re
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware


def to_camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def to_snake(s: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", s).lower()


class CamelCaseRequestMiddleware(BaseHTTPMiddleware):
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
