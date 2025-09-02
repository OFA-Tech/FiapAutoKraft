from fastapi.routing import APIRouter
from typing import List, Optional


class ControllerBase:
    def __init__(self, prefix: Optional[str] = None, tags: Optional[List[str]] = None):
        class_name = self.__class__.__name__.removesuffix("Controller")
        if prefix is None:
            prefix = f"/{class_name}"
        else:
            prefix = f"/{prefix.strip("/")}"
        if tags is None:
            tags = [class_name]
        else:
            tags.append(class_name)

        self.router = APIRouter(prefix=prefix, tags=tags)
