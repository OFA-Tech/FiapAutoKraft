from __future__ import annotations

import numpy as np


def apply_digital_zoom(frame: np.ndarray, zoom_factor: float) -> np.ndarray:
    if np.isclose(zoom_factor, 1.0):
        return frame
    height, width = frame.shape[:2]
    if zoom_factor < 1.0:
        new_width = max(1, int(width * zoom_factor))
        new_height = max(1, int(height * zoom_factor))
        resized = np.zeros_like(frame)
        scaled = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
        x_offset = (width - new_width) // 2
        y_offset = (height - new_height) // 2
        resized[y_offset : y_offset + new_height, x_offset : x_offset + new_width] = scaled
        return resized

    crop_width = max(1, int(width / zoom_factor))
    crop_height = max(1, int(height / zoom_factor))
    x_start = max(0, (width - crop_width) // 2)
    y_start = max(0, (height - crop_height) // 2)
    cropped = frame[y_start : y_start + crop_height, x_start : x_start + crop_width]
    return cv2.resize(cropped, (width, height), interpolation=cv2.INTER_LINEAR)


try:
    import cv2
except Exception:  # pragma: no cover - optional dependency
    cv2 = None  # type: ignore
