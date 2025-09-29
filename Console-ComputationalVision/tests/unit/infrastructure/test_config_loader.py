from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from infrastructure.config_loader import ArgConfigLoader


def test_parse_defaults_resolves_relative_model_path(tmp_path: Path) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir()

    loader = ArgConfigLoader(project_root=tmp_path)

    config = loader.parse([])

    assert config.project_root == tmp_path
    assert Path(config.initial_settings.model_path) == (models_dir / "best.pt").resolve()
