from enum import Enum


class ApiAuthorizationType(str, Enum):
    BASIC = "Basic"
    BEARER = "Bearer"