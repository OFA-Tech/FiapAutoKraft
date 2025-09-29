from pathlib import Path

from shared.paths import ensure_path_first, list_files_with_extensions


def test_list_files_with_extensions(tmp_path: Path) -> None:
    (tmp_path / "first.pt").write_text("data")
    (tmp_path / "second.PT").write_text("data")
    (tmp_path / "ignore.txt").write_text("nope")

    results = list_files_with_extensions(tmp_path, (".pt",))
    assert [path.name for path in results] == ["first.pt", "second.PT"]


def test_ensure_path_first_inserts(tmp_path: Path) -> None:
    base = ["a.pt", "b.pt"]
    ensured = ensure_path_first(base, "c.pt")
    assert ensured[0] == "c.pt"
    assert base == ["a.pt", "b.pt"]
    ensured_same = ensure_path_first(base, "a.pt")
    assert ensured_same == base
