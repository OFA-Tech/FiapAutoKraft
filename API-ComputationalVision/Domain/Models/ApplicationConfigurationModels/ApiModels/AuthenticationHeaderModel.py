from pydantic import BaseModel

from Domain.Enums.ApiAuthorizationType import ApiAuthorizationType


class AuthenticationHeaderModel(BaseModel):
    TYPE: ApiAuthorizationType
    AUTHORIZATION: str