from datetime import datetime
from typing import Dict

from dependency_injector.wiring import Provide, inject

from Domain.Enums.ApiRequestMethod import ApiRequestMethod
from Domain.Models.ApplicationConfigurationModels.ApiModels.RestApiRequestModel import RestApiRequestModel
from Domain.Models.ApplicationConfigurationModels.AppSettingsModel import AppSettingsModel, DataBaseConnectionModel, \
    ApiConnectionModel
from Domain.Models.ApplicationConfigurationModels.HealthReportModel import HealthReportModel, HealthEntryModel
from Domain.Utils import Utils
from Infrastructure.Data.Api.DefaultApiAccess import DefaultApiAccess
from Infrastructure.Data.Database.DefaultDatabaseAccess import DefaultDatabaseAccess


class HealthCheckServices:
    @inject
    def __init__(self,
                 db: DefaultDatabaseAccess = Provide["AppContainer.db_access"],
                 api: DefaultApiAccess = Provide["AppContainer.api_access"],
                 utils: Utils = Provide["AppContainer.utils"],
                 settings: AppSettingsModel = Provide["AppContainer.config"]):
        self._db = db
        self._api = api
        self._utils = utils
        self._settings = settings

    async def check(self) -> HealthReportModel:
        overall_start = datetime.now()
        entries: Dict[str, HealthEntryModel] = {}
        self_start = datetime.now()
        self_duration = datetime.now() - self_start
        entries["SELF"] = HealthEntryModel(
            data=None,
            description="Self check passed",
            duration=str(self_duration),
            exception=None,
            status="Healthy",
            tags=["api", "critical"]
        )
        entries.update(await self._check_all_databases())
        entries.update(await self._check_all_apis())

        overall_status= "Healthy" if all(value.status == "Healthy" for key, value in entries.items()) else "Unhealthy"

        return HealthReportModel(
            status=overall_status,
            totalDuration=str(datetime.now() - overall_start),
            entries=entries
        )

    #region Database Checks
    async def _check_all_databases(self) -> Dict[str, HealthEntryModel]:
        db_checks: Dict[str, HealthEntryModel] = {}
        for db in self._settings.DATABASE_CONNECTIONS:
            db_checks[f'DB-{db.DATABASE_ID}'] = await self._db_check(db)
        return db_checks

    async def _db_check(self, database: DataBaseConnectionModel) -> HealthEntryModel:
        start_time: datetime = datetime.now()
        try:
            response = await self._db.query_first(
                database,
                "SELECT 1 AS Test",
                None,
                True
            )
            return HealthEntryModel(
                data=response,
                description="Database connection successful",
                duration=str(datetime.now() - start_time),
                exception=None,
                status="Healthy" if response else "Unhealthy",
                tags=["db","critical", database.TYPE]
            )
        except Exception as e:
            return HealthEntryModel(
                data=None,
                description="Database connection failed",
                duration=str(datetime.now() - start_time),
                exception=str(e),
                status="Unhealthy",
                tags=["db","critical", database.TYPE]
            )
    #endregion

    #region API Checks
    async def _check_all_apis(self) -> Dict[str, HealthEntryModel]:
        api_checks: Dict[str, HealthEntryModel] = {}
        for api in self._settings.API_CONNECTIONS:
            api_checks[f'API-{api.API_ID}'] = await self._api_check(api)
        return api_checks

    async def _api_check(self, api: ApiConnectionModel) -> HealthEntryModel:
        start_time: datetime = datetime.now()
        try:
            response = await self._api.rest_api_request(
                RestApiRequestModel(
                    URL=f"{api.URL.rstrip("/")}/health",
                    Method=ApiRequestMethod.GET,
                    Headers=None,
                    Authentication=None,
                    QueryParameters=None,
                    Body=None
                )
            )
            data = None
            if response and response.content:
                if "application/json" in response.headers.get("content-type", "").lower():
                    try:
                        data = response.json()
                    except ValueError:
                        data = None
            return HealthEntryModel(
                data=data,
                description="API health check successful",
                duration=str(datetime.now() - start_time),
                exception=None,
                status="Healthy" if response.status_code == 200 else "Unhealthy",
                tags=["api", "external", api.API_ID]
            )
        except Exception as e:
            return HealthEntryModel(
                data=None,
                description="API health check failed",
                duration=str(datetime.now() - start_time),
                exception=str(e),
                status="Unhealthy",
                tags=["api", "external", api.API_ID]
            )

    #endregion
