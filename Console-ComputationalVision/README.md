# Console-ComputationalVision

A modular, dependency-injected scaffold for building console and GUI tooling around a computational vision pipeline. The project is organised into clear layers to support future expansion of the original prototype contained in `Console-ComputationalVision_BKP_Working`.

## Project Layout

```
Console-ComputationalVision/
  app/              # CLI/GUI entry points and dependency injection composition
  services/         # Application use cases orchestrating domain + data layers
  domain/           # Pure domain models and business logic
  data/             # Infrastructure adapters and repositories
  crosscutting/     # Logging, configuration, exceptions, shared utilities
  tests/            # Pytest-based test suite
```

## Getting Started

### Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run the sample CLI

```bash
python -m app.main --labels part --limit 1
```

The CLI bootstraps the dependency injection container, creates an execution scope, and invokes the vision inference use case. By default the container wires an in-memory detection provider so the command returns deterministic sample output.

### Run tests

```bash
pytest
```

## Architecture Diagram (ASCII)

```
+-------------------+        +-------------------+        +-------------------+
|  app.main CLI     | -----> |  services/use_cases | ----> |  domain/entities  |
|                   |        |  (VisionInference) |        |  (Detection DTOs) |
+-------------------+        +-------------------+        +-------------------+
          |                             |                             |
          |                             v                             |
          |                    +-------------------+                  |
          |                    | data/repositories | <----------------+
          |                    | (providers, repos)|
          |                             |
          v                             v
+-------------------+        +-------------------+
| crosscutting/config|        | crosscutting/log  |
| (pydantic settings)|        | (structlog setup) |
+-------------------+        +-------------------+
```

## Extending with Real Vision Capabilities

* Implement `YoloDetectionProvider` in `data/repositories.py` by porting the remaining inference logic from the backup repository. The structure already mirrors the previous `VisionService` responsibilities.
* Replace the default in-memory provider binding in `app/container.py` with the YOLO-backed implementation for real camera input.
* Expand `app/gui/` with widgets or a Tkinter front-end mirroring the original GUI.

## Tooling

* **Dependency management:** `requirements.txt`
* **Testing:** `pytest`
* **Linting:** `ruff`
* **Type checking:** `mypy`

## License

Refer to the root repository `LICENSE` file.
