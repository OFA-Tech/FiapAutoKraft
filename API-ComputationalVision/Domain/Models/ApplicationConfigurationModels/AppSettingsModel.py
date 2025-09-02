from pydantic import BaseModel

from Domain.Enums.ApiProtocolType import ApiProtocolType
from Domain.Enums.ApiRequestMethod import ApiRequestMethod
from Domain.Enums.DataBaseType import DataBaseType

class ApiEndPointConnectionModel(BaseModel):
    ENDPOINT_ID: str
    PATH: str
    METHOD: ApiRequestMethod
    PROTOCOL: ApiProtocolType

class ApiConnectionModel(BaseModel):
    API_ID: str
    URL: str
    ENDPOINTS: list[ApiEndPointConnectionModel]

class DataBaseConnectionModel(BaseModel):
    DATABASE_ID: str
    CONNECTION_STRING: str
    TYPE: DataBaseType

class AppSettingsModel(BaseModel):
    APP_NAME: str
    APP_VERSION: float
    DATABASE_CONNECTIONS: list[DataBaseConnectionModel]
    API_CONNECTIONS: list[ApiConnectionModel]
