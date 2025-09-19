# Console Computational Vision

This console application mirrors the API experience and lets you run the same
YOLOv12 models locally for quick experiments with images, video files or a live
camera feed. It also supports running the bundled TensorFlow/Keras image
classifier trained on the product catalog labels.

## 🚀 Getting started

1. Create a virtual environment and install the requirements:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2. The console defaults to the bundled TensorFlow/Keras classifier (preferring
   the `keras_models/keras_model.keras` or `keras_models/keras_model.h5`
   checkpoints and automatically falling back to the
   `keras_models/converted_savedmodel/model.savedmodel` directory when the
   packaged weights are missing or incompatible with your local TensorFlow
   build). Whenever the YOLO weights are available (e.g. `yolov8n.pt`) the
   console reuses them to propose bounding boxes and labels the detections with
   the Keras classifier result. If you want to run the YOLO detector directly,
   download or reuse the weights referenced by the API and place them in the
   repository root or set the `YOLOV12_MODEL_PATH` environment variable to point
   to your weights file.

3. Run the console application:

```bash
python main.py --source 0                # Default webcam using the Keras classifier
python main.py --source path/to/image.jpg
python main.py --source path/to/video.mp4
python main.py --backend yolo            # Force YOLO even when the default is Keras
```

Press `q` or `Esc` while the preview window is focused to stop the detection
loop. For static images, close the preview window or press any key while the
window has focus.

## ⚙️ Useful parameters

- `--model`: path to the model weights (supports YOLO `.pt` files or the bundled
  Keras assets). When omitted the app looks for `KERAS_MODEL_PATH` or the
  packaged classifier under `keras_models/`.
- `--confidence`: minimum confidence score required for a detection.
- `--iou`: Intersection-over-Union threshold used by non-max suppression.
- `--max-detections`: maximum number of detections drawn per frame.
- `--device`: optional torch device (e.g. `cuda:0` or `cpu`).
- `--labels`: path to a custom `labels.txt` file. When omitted the app searches the
  `keras_models` directory and will only display detections for the labels found there.
- `--backend`: select the inference engine (`auto`, `yolo` or `keras`). The
  default `auto` mode will prioritise the packaged Keras classifier.

## 📝 Notes

- The preview window displays bounding boxes, class names, confidence values
  and the `(x, y)` coordinates of each detection's center.
- The frame rate indicator at the top-left corner helps you monitor the
  inference speed of your hardware.
- When a custom labels file is present under `keras_models/converted_savedmodel/labels.txt`
  only those classes will be displayed in the output, ensuring the detections stay
  focused on the trained products.
- In Keras mode the application still renders detection boxes (when YOLO weights
  are available) and logs each labelled detection with its confidence and center
  coordinates to the terminal. If the YOLO weights are missing the workflow
  gracefully falls back to whole-frame classification with the top predictions
  overlayed on the video feed. Ensure TensorFlow is installed (included via
  `requirements.txt`) before enabling this workflow. When the `.h5` checkpoint
  cannot be deserialised because of Keras/TensorFlow version differences the app
  seamlessly loads the bundled SavedModel via `tf.saved_model` instead, so no
  manual conversion is required.
- A compatibility shim automatically handles older TensorFlow builds that do not yet
  support the `groups` argument for `DepthwiseConv2D` when loading the bundled
  classifier weights.
