from typing import Any, Dict, Optional

from fastapi import status

from .camelize import CamelAPIResponse


class APIResponse(CamelAPIResponse):
    def __init__(
        self,
        data: Any = None,
        message: Optional[str] = None,
        status_code: int = status.HTTP_200_OK,
        errors: Optional[Dict[str, Any]] = None,
        success: Optional[bool] = None,
        **kwargs,
    ):
        if success is None:
            success = status_code < 400

        content = {"success": success}
        if message:
            content["message"] = message
        if data is not None:
            content["data"] = data
        if errors:
            content["errors"] = errors

        super().__init__(content=content, status_code=status_code, **kwargs)
