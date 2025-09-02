from typing import Optional

from pydantic import BaseModel

from Domain.Enums.ApiRequestMethod import ApiRequestMethod
from Domain.Models.ApplicationConfigurationModels.ApiModels.AuthenticationHeaderModel import AuthenticationHeaderModel


class RestApiRequestModel(BaseModel):
    URL: str
    Method: ApiRequestMethod
    Timeout: Optional[int] = 30
    QueryParameters: Optional[dict]
    Headers: Optional[dict]
    Body: Optional[str]
    Authentication: Optional[AuthenticationHeaderModel]

