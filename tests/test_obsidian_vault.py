from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / ".paperlab" / "obsidian_vault.py"
SPEC = importlib.util.spec_from_file_location("obsidian_vault", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_bootstrap_creates_curated_three_level_structure_without_overwrite(tmp_path: Path):
    vault = tmp_path / "个人知识网络"
    first = MODULE.bootstrap_vault(vault)

    home = vault / "00_首页" / "00_从这里开始.canvas"
    assert first["created"] >= 60
    assert home.exists()
    assert not (vault / "00_首页" / "个人知识网络.canvas").exists()
    assert not (vault / "10_深度学习与CNN" / "00_总览.canvas").exists()

    module_dirs = sorted((vault / "10_深度学习与CNN").glob("0[1-6]_*/"))
    assert len(module_dirs) == 6
    for module_dir in module_dirs:
        title = module_dir.name[3:]
        assert (module_dir / f"00_{title}.canvas").exists()
        assert (module_dir / f"00_{title}-导览.md").exists()
        assert not (module_dir / "模块.canvas").exists()
        assert not (module_dir / "模块总览.md").exists()

    concept_notes = [
        path
        for module_dir in module_dirs
        for path in module_dir.glob("[0-9][0-9]_*.md")
        if not path.name.startswith("00_")
    ]
    assert len(concept_notes) == 45
    assert all("<!-- knowledge-nav:start -->" in path.read_text(encoding="utf-8") for path in concept_notes)
    for path in concept_notes:
        text = path.read_text(encoding="utf-8")
        assert "<!-- KNOWLEDGE:AUTO:START -->" in text
        assert "<!-- KNOWLEDGE:AUTO:END -->" in text
        assert "## 人工笔记" in text
        assert "## 核心机制" in text
        assert "## 具体例子" in text
        assert "## 在实际工作中的位置" in text
        assert "## 练习或实验" in text
        assert "## 证据与边界" in text
        assert "## 常见误区" in text
        assert "补充一个可以" not in text
        assert "说明这个概念解决" not in text

    lab_dir = vault / "10_深度学习与CNN" / "08_实验项目"
    lab_notes = sorted(lab_dir.glob("[0-9][0-9]_*.md"))
    assert len(lab_notes) == 4
    assert all("cnn_labs.py" in path.read_text(encoding="utf-8") for path in lab_notes)
    assert (lab_dir / "cnn_labs.py").read_text(encoding="utf-8") == (ROOT / ".paperlab" / "cnn_labs.py").read_text(encoding="utf-8")

    home_canvas = json.loads(home.read_text(encoding="utf-8"))
    home_files = [node["file"] for node in home_canvas["nodes"] if node["type"] == "file"]
    assert len(home_files) == 7
    assert sum(path.endswith(".canvas") for path in home_files) == 6
    assert any("07_论文与证据/00_论文导览.md" in path for path in home_files)

    for canvas_path in vault.rglob("*.canvas"):
        canvas = json.loads(canvas_path.read_text(encoding="utf-8"))
        node_ids = [node["id"] for node in canvas["nodes"]]
        assert len(node_ids) == len(set(node_ids))
        for node in canvas["nodes"]:
            if node["type"] == "file":
                assert "99_自动导入" not in node["file"]
                assert (vault / node["file"]).exists(), (canvas_path, node["file"])

    graph = json.loads((vault / ".obsidian" / "graph.json").read_text(encoding="utf-8"))
    assert graph["search"] == "tag:#knowledge"
    assert graph["hideUnresolved"] is True
    assert graph["showAttachments"] is False
    assert graph["showOrphans"] is False
    assert graph["showArrow"] is True
    assert len(graph["colorGroups"]) == 3

    edited = vault / "10_深度学习与CNN" / "03_卷积神经网络" / "02_卷积运算.md"
    edited.write_text("人工修改\n", encoding="utf-8")
    second = MODULE.bootstrap_vault(vault)
    assert second["created"] == 0
    assert edited.read_text(encoding="utf-8") == "人工修改\n"


def test_bootstrap_adds_mathjax_formulas_and_tiered_paper_roadmap(tmp_path: Path):
    vault = tmp_path / "个人知识网络"
    MODULE.bootstrap_vault(vault)

    roadmap = vault / "10_深度学习与CNN" / "07_论文与证据" / "00_必读论文路线.md"
    text = roadmap.read_text(encoding="utf-8")
    assert "## 必读主线（12 篇）" in text
    assert "## 按任务必读（5 篇）" in text
    assert "## 扩展阅读（3 篇）" in text
    assert "Deep Residual Learning for Image Recognition" in text
    assert "An Image is Worth 16x16 Words" in text
    assert "Faster R-CNN" in text
    assert "精读完成" in text
    assert "待导入与精读" in text
    assert "[[10_深度学习与CNN/07_论文与证据/01_LeNet]]" in text

    resnet = vault / "10_深度学习与CNN" / "04_经典与现代架构" / "05_ResNet.md"
    resnet_text = resnet.read_text(encoding="utf-8")
    assert "## 推荐论文" in resnet_text
    assert "Deep Residual Learning for Image Recognition" in resnet_text
    assert "[[10_深度学习与CNN/07_论文与证据/00_必读论文路线|" in resnet_text

    for title, formula in MODULE.FORMULAS.items():
        matches = list((vault / "10_深度学习与CNN").glob(f"0[1-6]_*/*_{title}.md"))
        assert len(matches) == 1, title
        note = matches[0].read_text(encoding="utf-8")
        assert "## 公式与符号" in note, title
        assert formula in note, title
        assert "\\(" not in note and "\\[" not in note, title


def test_migration_preserves_note_body_merges_graph_settings_and_is_idempotent(tmp_path: Path):
    assert hasattr(MODULE, "migrate_vault_layout")
    vault = tmp_path / "个人知识网络"
    old_module = vault / "10_深度学习与CNN" / "03_卷积神经网络"
    old_module.mkdir(parents=True)
    old_note = old_module / "卷积运算.md"
    old_note.write_text(
        '---\ntype: concept\nstatus: 学习中\nmodule: "[[10_深度学习与CNN/03_卷积神经网络/模块总览]]"\n---\n\n'
        "# 卷积运算\n\n我自己补充的内容，必须保留。\n\n"
        "- 属于：[[10_深度学习与CNN/03_卷积神经网络/模块总览]]\n"
        "- 证据支持：[[10_深度学习与CNN/90_论文证据/论文-CNN综述]]\n",
        encoding="utf-8",
    )
    (old_module / "模块总览.md").write_text("旧导览\n", encoding="utf-8")
    (old_module / "模块.canvas").write_text('{"nodes": [], "edges": []}\n', encoding="utf-8")
    graph_path = vault / ".obsidian" / "graph.json"
    graph_path.parent.mkdir(parents=True)
    graph_path.write_text('{"customSetting": 7, "search": ""}\n', encoding="utf-8")

    dry_run = MODULE.migrate_vault_layout(vault, dry_run=True)
    assert dry_run["moved"] == 3
    assert old_note.exists()
    assert not list(vault.glob(".paperlab-backup/*"))

    migrated = MODULE.migrate_vault_layout(vault)
    new_note = old_module / "02_卷积运算.md"
    assert migrated["conflicts"] == []
    assert migrated["moved"] == 3
    assert Path(migrated["backup_dir"]).exists()
    assert new_note.exists()
    assert not old_note.exists()
    text = new_note.read_text(encoding="utf-8")
    assert "我自己补充的内容，必须保留。" in text
    assert "<!-- knowledge-nav:start -->" in text
    assert "<!-- KNOWLEDGE:AUTO:START -->" in text
    assert "<!-- KNOWLEDGE:AUTO:END -->" in text
    assert "## 人工笔记\n\n我自己补充的内容，必须保留。" in text
    assert "## 核心机制" in text
    assert "## 具体例子" in text
    assert "order: 2" in text
    assert "00_卷积神经网络-导览" in text
    assert "[[10_深度学习与CNN/03_卷积神经网络/00_卷积神经网络-导览]]" in text
    assert "[[10_深度学习与CNN/07_论文与证据/04_CNN综述]]" in text
    assert "模块总览" not in text
    assert "90_论文证据" not in text

    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    assert graph["customSetting"] == 7
    assert graph["search"] == "tag:#knowledge"
    assert graph["hideUnresolved"] is True

    repeated = MODULE.migrate_vault_layout(vault)
    assert repeated["moved"] == 0
    assert repeated["rewritten"] == 0
    assert repeated["backup_dir"] == ""


def test_migration_aborts_before_writes_when_destination_conflicts(tmp_path: Path):
    assert hasattr(MODULE, "migrate_vault_layout")
    vault = tmp_path / "vault"
    module_dir = vault / "10_深度学习与CNN" / "03_卷积神经网络"
    module_dir.mkdir(parents=True)
    old_note = module_dir / "卷积运算.md"
    new_note = module_dir / "02_卷积运算.md"
    old_note.write_text("old\n", encoding="utf-8")
    new_note.write_text("new\n", encoding="utf-8")

    with pytest.raises(FileExistsError, match="02_卷积运算.md"):
        MODULE.migrate_vault_layout(vault)

    assert old_note.read_text(encoding="utf-8") == "old\n"
    assert new_note.read_text(encoding="utf-8") == "new\n"
    assert not list(vault.glob(".paperlab-backup/*"))


def test_refresh_replaces_only_auto_block_and_preserves_human_section_bytes(tmp_path: Path):
    vault = tmp_path / "vault"
    MODULE.bootstrap_vault(vault)
    note = vault / "10_深度学习与CNN" / "03_卷积神经网络" / "02_卷积运算.md"
    text = note.read_text(encoding="utf-8")
    text = text.replace(
        text[text.index("<!-- KNOWLEDGE:AUTO:START -->") : text.index("<!-- KNOWLEDGE:AUTO:END -->") + len("<!-- KNOWLEDGE:AUTO:END -->")],
        "<!-- KNOWLEDGE:AUTO:START -->\n旧自动内容\n<!-- KNOWLEDGE:AUTO:END -->",
    )
    human = "\n\n我的公式：$y=wx+b$  \n旧链接也原样保留：[[10_深度学习与CNN/03_卷积神经网络/模块总览]]\n"
    text = text.split("## 人工笔记", 1)[0] + "## 人工笔记" + human
    note.write_text(text, encoding="utf-8")

    refreshed = MODULE.migrate_vault_layout(vault)
    result = note.read_text(encoding="utf-8")
    assert refreshed["rewritten"] >= 1
    assert "旧自动内容" not in result
    assert result.split("## 人工笔记", 1)[1] == human

    repeated = MODULE.migrate_vault_layout(vault)
    assert repeated["rewritten"] == 0


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


def test_sync_normalizes_latex_delimiters_for_obsidian(tmp_path: Path):
    project = tmp_path / "project"
    source = project / "papers" / "paper.md"
    source.parent.mkdir(parents=True)
    source.write_text("行内 \\(x+y\\)\n\n\\[\nz=1\n\\]\n", encoding="utf-8")

    vault = tmp_path / "vault"
    result = MODULE.sync_artifacts(project, tmp_path / "pdf", vault)

    imported = vault / "99_自动导入" / "精读稿" / "paper.md"
    assert result["copied"] == 1
    assert imported.read_text(encoding="utf-8") == "行内 $x+y$\n\n$$\nz=1\n$$\n"
    assert MODULE.sync_artifacts(project, tmp_path / "pdf", vault)["unchanged"] == 1
