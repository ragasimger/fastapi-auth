import re
from typing import Annotated

from pydantic import BaseModel, Field, field_validator, model_validator


class PydanticBaseModel(BaseModel):
    class Config:
        extra = "forbid"
