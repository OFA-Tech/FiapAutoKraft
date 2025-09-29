from __future__ import annotations

from ..domain.camera.camera_repository import CameraRepository


class ListCamerasUseCase:
    def __init__(self, repository: CameraRepository) -> None:
        self._repository = repository

    def execute(self):
        return list(self._repository.list_cameras())
