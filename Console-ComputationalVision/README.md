# Console Computational Vision

This console application mirrors the API experience and lets you run the same
YOLOv12 models locally for quick experiments with images, video files or a live
camera feed.

## 🚀 Getting started

1. Create a virtual environment and install the requirements:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2. Download or reuse the YOLO weights referenced by the API (e.g. `yolov8n.pt`)
and place them in the repository root, or set the `YOLOV12_MODEL_PATH`
environment variable to point to your weights file.

3. Run the console application:

```bash
python main.py --source 0                # Default webcam
python main.py --source path/to/image.jpg
python main.py --source path/to/video.mp4
```

Press `q` or `Esc` while the preview window is focused to stop the detection
loop. For static images, close the preview window or press any key while the
window has focus.

## ⚙️ Useful parameters

- `--model`: path to the YOLO model weights (defaults to `YOLOV12_MODEL_PATH`
  or `yolov8n.pt`).
- `--confidence`: minimum confidence score required for a detection.
- `--iou`: Intersection-over-Union threshold used by non-max suppression.
- `--max-detections`: maximum number of detections drawn per frame.
- `--device`: optional torch device (e.g. `cuda:0` or `cpu`).

## 📝 Notes

- The preview window displays bounding boxes, class names, confidence values
  and the `(x, y)` coordinates of each detection's center.
- The frame rate indicator at the top-left corner helps you monitor the
  inference speed of your hardware.
