from dependency_injector.wiring import Provide, inject
from fastapi import Depends, HTTPException, status

from App.Controllers.ControllerBase import ControllerBase
from Domain.Models.Vision.ImageDetectionRequestModel import ImageDetectionRequestModel
from Domain.Models.Vision.ImageDetectionResponseModel import ImageDetectionResponseModel
from Domain.Models.Vision.VideoDetectionRequestModel import VideoDetectionRequestModel
from Domain.Models.Vision.VideoDetectionResponseModel import VideoDetectionResponseModel
from Infrastructure.CrossCutting.InjectionConfiguration import AppContainer
from Services.ApplicationServices.YoloV12DetectionService import YoloV12DetectionService


class VisionController(ControllerBase):
    """REST endpoints exposing YOLOv12 object detection capabilities."""

    def __init__(self) -> None:
        super().__init__()

        @self.router.post(
            "/detect-image",
            response_model=ImageDetectionResponseModel,
            summary="Detect objects in an image using YOLOv12",
        )
        @inject
        async def detect_image(
            request: ImageDetectionRequestModel,
            service: YoloV12DetectionService = Depends(Provide[AppContainer.yolo_v12_service]),
        ) -> ImageDetectionResponseModel:
            if service is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Object detection service is not available.",
                )

            try:
                return await service.detect_image(request.image_base64)
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(exc),
                ) from exc
            except RuntimeError as exc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(exc),
                ) from exc

        @self.router.post(
            "/detect-video",
            response_model=VideoDetectionResponseModel,
            summary="Detect objects in a video using YOLOv12",
        )
        @inject
        async def detect_video(
            request: VideoDetectionRequestModel,
            service: YoloV12DetectionService = Depends(Provide[AppContainer.yolo_v12_service]),
        ) -> VideoDetectionResponseModel:
            if service is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Object detection service is not available.",
                )

            try:
                return await service.detect_video(
                    video_data=request.video_base64,
                    frame_interval=request.frame_interval,
                    max_frames=request.max_frames,
                )
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(exc),
                ) from exc
            except RuntimeError as exc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(exc),
                ) from exc
