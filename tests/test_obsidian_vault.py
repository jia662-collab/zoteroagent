from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / ".paperlab" / "obsidian_vault.py"
SPEC = importlib.util.spec_from_file_location("obsidian_vault", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_bootstrap_creates_complete_clickable_structure_without_overwrite(tmp_path: Path):
    vault = tmp_path / "个人知识网络"
    first = MODULE.bootstrap_vault(vault)

    assert first["created"] >= 60
    assert (vault / "00_首页" / "个人知识网络.canvas").exists()
    assert (vault / "10_深度学习与CNN" / "00_总览.canvas").exists()
    assert len(list((vault / "10_深度学习与CNN").glob("0?_*/*.canvas"))) == 6
    concept_notes = [
        path
        for path in (vault / "10_深度学习与CNN").glob("0?_*/*.md")
        if path.name != "模块总览.md"
    ]
    assert len(concept_notes) == 45

    for canvas_path in vault.rglob("*.canvas"):
        canvas = json.loads(canvas_path.read_text(encoding="utf-8"))
        node_ids = [node["id"] for node in canvas["nodes"]]
        assert len(node_ids) == len(set(node_ids))
        for node in canvas["nodes"]:
            if node["type"] == "file":
                assert (vault / node["file"]).exists(), (canvas_path, node["file"])

    edited = vault / "10_深度学习与CNN" / "03_卷积神经网络" / "卷积运算.md"
    edited.write_text("人工修改\n", encoding="utf-8")
    second = MODULE.bootstrap_vault(vault)
    assert second["created"] == 0
    assert edited.read_text(encoding="utf-8") == "人工修改\n"


def test_sync_is_idempotent_atomic_and_preserves_missing_sources(tmp_path: Path):
    project = tmp_path / "project"
    pdf_dir = tmp_path / "pdf"
    vault = tmp_path / "vault"
    samples = {
        project / "papers" / "paper.md": "精读",
        project / "translations" / "paper.md": "对照",
        project / "evidence" / "paper.json": "{}",
        pdf_dir / "paper.pdf": "%PDF-sample",
    }
    for path, content in samples.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    first = MODULE.sync_artifacts(project, pdf_dir, vault)
    assert first["copied"] == 4
    assert first["stale"] == 0
    assert not list(vault.rglob("*.tmp"))

    second = MODULE.sync_artifacts(project, pdf_dir, vault)
    assert second["copied"] == 0
    assert second["unchanged"] == 4

    removed = project / "papers" / "paper.md"
    removed.unlink()
    third = MODULE.sync_artifacts(project, pdf_dir, vault)
    preserved = vault / "99_自动导入" / "精读稿" / "paper.md"
    assert third["stale"] == 1
    assert preserved.read_text(encoding="utf-8") == "精读"
    manifest = json.loads((vault / "99_自动导入" / "_manifest.json").read_text(encoding="utf-8"))
    assert len({entry["destination"] for entry in manifest["files"]}) == 4
    assert any(entry["status"] == "待同步" for entry in manifest["files"])
