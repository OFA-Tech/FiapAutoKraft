from App.Controllers.ControllerBase import ControllerBase


class HelloWorldController(ControllerBase):
    def __init__(self):
        super().__init__()

        @self.router.get("/")
        async def root():
            return {"message": "Hello World"}

        @self.router.get("/hello/{name}")
        async def say_hello(name: str):
            return {"message": f"Hello {name}"}