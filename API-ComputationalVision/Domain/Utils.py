import functools

from Domain.Models.ApplicationConfigurationModels.AppSettingsModel import AppSettingsModel
import asyncio
import os
import shutil
import json


class Utils:
    @staticmethod
    def read_file(file_path: str) -> str:
        with open(file_path, 'r') as file:
            return file.read()

    def read_appsettings(self) -> AppSettingsModel:
        base_path: str = os.path.dirname(os.path.dirname(__file__))
        appsettings_path: str = os.path.join(base_path, 'App', 'appsettings.json')
        file_content: str = self.read_file(appsettings_path)
        settings: dict = json.loads(file_content)
        return AppSettingsModel(**settings)

    @staticmethod
    def parse_mysql(conn_str: str):
        config = {}
        for part in conn_str.split(";"):
            if "=" in part:
                k, v = part.split("=", 1)
                config[k.strip().lower()] = v.strip()
        return {
            "host": config.get("server", "localhost"),
            "user": config.get("user id", ""),
            "password": config.get("password", ""),
            "database": config.get("initial catalog", ""),
            "connect_timeout": int(config.get("connect timeout", "5"))
        }

    @staticmethod
    def wrap_async(check_func):
        @functools.wraps(check_func)
        def sync_wrapper():
            return asyncio.run(check_func())

        return sync_wrapper
