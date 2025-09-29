# Console Computational Vision Architecture

```
+------------------+
| Presentation     |  Tkinter GUI (`presentation/`)
+------------------+
          |
          v
+------------------+
| Application      |  Use cases & orchestrators (`application/`)
+------------------+
          |
          v
+------------------+
| Domain           |  Entities, interfaces, events (`domain/`)
+------------------+
          |
          v
+------------------+
| Infrastructure   |  Adapters (OpenCV, YOLO, GRBL) (`infrastructure/`)
+------------------+
```

## Layers

- **Presentation** renders the GUI and never talks to hardware directly. It depends on
  application use cases and reacts to domain events published on the event bus.
- **Application** contains the orchestration logic (start/stop detection, send coordinates,
  polling, etc.). It depends only on domain interfaces and uses constructor injection for
  collaborators.
- **Domain** defines value objects, entities, DTOs and the interfaces implemented by the
  infrastructure adapters. No framework code lives here.
- **Infrastructure** implements the domain interfaces using OpenCV, Ultralytics YOLO and the
  GRBL serial protocol. Adapters expose instrumentation hooks so that the presentation can
  surface diagnostic information.

## Dependency Injection

`main.py` acts as the composition root. It wires the following
bindings:

| Interface                     | Implementation                   |
|-------------------------------|----------------------------------|
| `CameraRepository`            | `OpenCvCameraRepository`         |
| `DetectorFactory`             | `YoloDetectorFactory` (produces `YoloVxDetector` instances per session) |
| `GcodeSender`                 | `SerialGcodeSender`              |
| `ModelStore`                  | Filesystem-backed model store    |
| `EventBus`                    | Simple thread-safe publish/subscribe bus |

The DI container is deliberately lightweight: the `build_app` function constructs concrete
instances, injects them into the appropriate use cases and then passes those to the
`GuiApp`. All injection happens via constructors, and there are no module-level singletons.
Detectors are never bound directly; instead the `DetectorFactory` creates a fresh
`YoloVxDetector` for each detection run so alternate implementations only require a new
factory binding.

### Lifecycles

- **Singletons**: Event bus, logger hierarchy, model store, settings store, dispatcher,
  poller and serial sender live for the entire application lifetime.
- **Per-session**: The detection controller opens a camera stream and creates a detector
  instance for each detection session.
- **Transients**: Use case instances construct DTOs on the fly when users interact with the
  GUI.

Swapping an adapter (for example, a different detector) requires adding a new implementation
in `infrastructure/` and updating the binding in `build_app`.

## Testing Strategy

- Unit tests live under `tests/unit/` and target domain entities, the event bus, command
  dispatcher, position poller, shared helper modules (`shared/ui_controls.py`,
  `shared/logging_utils.py`, `shared/scheduling.py`, `shared/paths.py`, `shared/validation.py`)
  and the detection controller using fake adapters.
- `tests/integration/test_system_smoke.py` provides a smoke test that wires the entire stack
  with fakes to ensure detection events and G-code commands flow end-to-end without touching
  real hardware. `tests/integration/test_detector_factory.py` exercises the detector factory
  wiring to ensure a detector can be created and invoked without a concrete camera feed.

## Shared helpers

The `shared/` package hosts cross-cutting utilities that remove duplication between the GUI
widgets and background services:

- `ui_controls.py` centralises combobox population, widget enable/disable toggling and other
  small Tkinter helpers.
- `logging_utils.py` funnels log lines into text widgets while enforcing the 150-line FIFO
  requirement for both Python and G-code logs.
- `scheduling.py` provides the `IntervalScheduler` used by the position poller to implement
  the skip-tick policy when the sender is busy or disconnected.
- `validation.py` contains reusable numeric parsers so presentation code surfaces consistent
  error messages.
- `paths.py` encapsulates model discovery and path list normalisation for the filesystem
  adapters.
