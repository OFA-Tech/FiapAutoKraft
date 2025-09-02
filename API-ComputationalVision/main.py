from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from Domain.Utils import Utils
from Infrastructure.CrossCutting.InjectionConfiguration import AppContainer
from Infrastructure.CrossCutting.ControllerLoader import ControllerLoader

utils: Utils = Utils()
app_settings = utils.read_appsettings()

container = AppContainer()
container.config.override(app_settings.model_dump())
app = FastAPI(
    title=app_settings.APP_NAME,
    version=str(app_settings.APP_VERSION),
    docs_url="/docs",
    redoc_url=None,
    openapi_url=f"/docs/v{app_settings.APP_VERSION}/openapi.json"
)

app.container = container

controllerLoader: ControllerLoader = ControllerLoader()
controllerLoader.auto_register_controllers(app=app, package="App.Controllers", container=container)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.openapi = ControllerLoader.custom_openapi(app, app_settings)
