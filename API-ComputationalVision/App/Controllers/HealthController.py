from dependency_injector.wiring import Provide, inject
from fastapi import Depends

from App.Controllers.ControllerBase import ControllerBase
from Domain.Models.ApplicationConfigurationModels.HealthReportModel import HealthReportModel
from Services.ApplicationServices.HealthCheckServices import HealthCheckServices
from Infrastructure.CrossCutting.InjectionConfiguration import AppContainer


class HealthController(ControllerBase):
    def __init__(self):
        super().__init__()

        @self.router.get("", response_model=HealthReportModel)
        @inject
        async def root(service: HealthCheckServices = Depends(Provide[AppContainer.health_check_service])) -> HealthReportModel:
            return await service.check()