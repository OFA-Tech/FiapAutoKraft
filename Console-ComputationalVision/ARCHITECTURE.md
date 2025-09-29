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

`console_computational_vision.main` acts as the composition root. It wires the following
bindings:

| Interface                     | Implementation                   |
|-------------------------------|----------------------------------|
| `CameraRepository`            | `OpenCvCameraRepository`         |
| `DetectorFactory`             | `YoloDetectorFactory`            |
| `GcodeSender`                 | `SerialGcodeSender`              |
| `ModelStore`                  | Filesystem-backed model store    |
| `EventBus`                    | Simple thread-safe publish/subscribe bus |

The DI container is deliberately lightweight: the `build_app` function constructs concrete
instances, injects them into the appropriate use cases and then passes those to the
`GuiApp`. All injection happens via constructors, and there are no module-level singletons.

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
  dispatcher, position poller and detection controller using fake adapters.
- `tests/integration/test_system_smoke.py` provides a smoke test that wires the entire stack
  with fakes to ensure detection events and G-code commands flow end-to-end without touching
  real hardware.
