# Console-ComputationalVision

A modular, dependency-injected scaffold for building console and GUI tooling around a computational vision pipeline. The project keeps the layering from the legacy prototype while adding a Tkinter operator console that launches by default.

## Project Layout

```
Console-ComputationalVision/
  app/              # CLI/GUI entry points and dependency container
  services/         # Application use cases orchestrating domain + data layers
  domain/           # Pure domain models and business logic
  data/             # Infrastructure adapters and repositories
  crosscutting/     # Logging, configuration, shared utilities
  tests/            # Pytest-based test suite
```

## Getting Started

### Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Launch the GUI

```bash
python -m app.main
```

The GUI starts with the in-memory detection provider so that the interface can be exercised without a camera. Use the **Start** button to run repeated inference cycles and watch the detections table update.

### Run in CLI mode

```bash
python -m app.main --cli --labels part tool --limit 1
```

CLI mode is useful for headless environments or quick smoke tests. Add `--use-yolo` to switch to the real YOLO-backed provider once the optional dependencies are installed.

### Run tests

```bash
pytest
```

## Architecture Diagram (ASCII)

```
+---------------------+        +---------------------+        +-------------------+
|  app/ (CLI + GUI)   | -----> | services/use_cases  | -----> |  domain/entities  |
|  container + Tk     |        |  (VisionInference)  |        |  (Detection DTOs) |
+---------------------+        +---------------------+        +-------------------+
          |                               |
          |                               v
          |                      +---------------------+
          |                      | data/repositories   |
          |                      | (providers, repos)  |
          |                               |
          v                               v
+---------------------+        +---------------------+
| crosscutting/config |        | crosscutting/logging|
| (env-based settings)|        | (stdlib logging)    |
+---------------------+        +---------------------+
```

## Extending with Real Vision Capabilities

* Wire the YOLO backend by calling `container.use_yolo_backend()` in `app/main.py` or by passing `--use-yolo` on the CLI.
* Port any remaining functionality from the legacy `VisionService` into `YoloDetectionProvider` if additional features are required.
* Expand `app/gui/` with camera previews and GRBL controls from the original Tkinter application.

## Tooling

* **Dependency management:** `requirements.txt`
* **Testing:** `pytest`
* **Linting:** `ruff`
* **Type checking:** `mypy`

## License

Refer to the root repository `LICENSE` file.
