from dependency_injector import containers, providers
from Domain.Models.ApplicationConfigurationModels.AppSettingsModel import AppSettingsModel
from Domain.Utils import Utils
from Infrastructure.Data.Api.DefaultApiAccess import DefaultApiAccess
from Infrastructure.Data.Database.DefaultDatabaseAccess import DefaultDatabaseAccess
from Services.ApplicationServices.HealthCheckServices import HealthCheckServices
from Services.ApplicationServices.YoloV12DetectionService import YoloV12DetectionService


class AppContainer(containers.DeclarativeContainer):
    config = providers.Configuration()
    app_settings = providers.Singleton(AppSettingsModel.model_validate, config)
    #region Extras
    utils = providers.Singleton(Utils)
    #endregion

    #region Database
    db_access = providers.Factory(DefaultDatabaseAccess, utils=utils)
    #endregion

    #region API
    api_access = providers.Factory(DefaultApiAccess, utils=utils)
    #endregion

    #region Services
    health_check_service = providers.Factory(HealthCheckServices,
                                             db=db_access,
                                             api=api_access,
                                             utils=utils,
                                             settings=app_settings)
    yolo_v12_service = providers.Singleton(YoloV12DetectionService)

