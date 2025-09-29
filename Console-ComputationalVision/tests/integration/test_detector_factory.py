import sys
from types import ModuleType, SimpleNamespace

import numpy as np
import pytest

from domain.camera.camera import Frame


class _DummyYOLO:
    def __init__(self, _path: str) -> None:
        self.names = {0: "object"}
        self.model = SimpleNamespace(args={"imgsz": 8})

    def to(self, _device: str) -> None:  # pragma: no cover - behaviourless
        return None

    def predict(self, *_args, **_kwargs):
        return [SimpleNamespace(boxes=[])]


@pytest.fixture()
def detector_module():
    class _StubCv2(ModuleType):
        def __getattr__(self, name):
            if name.isupper():
                return 0
            return lambda *args, **kwargs: None

    class _StubTorch(ModuleType):
        class cuda:  # noqa: N801 - mimic attribute casing
            @staticmethod
            def is_available() -> bool:
                return False

        @staticmethod
        def inference_mode():
            class _Context:
                def __enter__(self):
                    return None

                def __exit__(self, exc_type, exc, tb):
                    return False

            return _Context()

    sys.modules.setdefault("cv2", _StubCv2("cv2"))
    stub_cvzone = ModuleType("cvzone")
    stub_cvzone.putTextRect = lambda *args, **kwargs: None
    sys.modules.setdefault("cvzone", stub_cvzone)
    sys.modules.setdefault("torch", _StubTorch("torch"))
    stub_ultralytics = ModuleType("ultralytics")
    stub_ultralytics.YOLO = _DummyYOLO
    sys.modules.setdefault("ultralytics", stub_ultralytics)

    import importlib

    module = importlib.import_module("infrastructure.yolovX_detector")
    return module


def test_factory_creates_detector_and_infers(detector_module):
    import logging

    factory = detector_module.YoloDetectorFactory(logging.getLogger("test"))
    detector = factory.create("model.pt", device="cpu")

    frame = Frame(data=np.zeros((8, 8, 3), dtype=np.uint8), timestamp=0.0)
    result = detector.infer(frame)

    assert result.boxes == ()
    assert result.annotated_frame.shape == frame.data.shape
    assert isinstance(result.duration_ms, float)
    assert detector.labels() == ("object",)
