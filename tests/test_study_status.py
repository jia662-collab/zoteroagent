from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / ".paperlab" / "paperlab.py"


def run_study_status(vault: Path, project_status: Path, output: Path) -> dict:
    completed = subprocess.run(
        [
            sys.executable,
            str(ENGINE),
            "study-status",
            "--vault",
            str(vault),
            "--project-status",
            str(project_status),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    return json.loads(completed.stdout)


def write_note(path: Path, *, note_type: str, fields: dict[str, str], body: str = "") -> None:
    frontmatter = "\n".join(f"{key}: {value}" for key, value in fields.items())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\ntype: {note_type}\n{frontmatter}\n---\n\n# {path.stem}\n\n{body}\n",
        encoding="utf-8",
    )


def write_project_status(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """# 当前进度

- 项目：`demo`
- 阶段：reading
- 下一步：学习卷积基础
- 已处理论文：2
""",
        encoding="utf-8",
    )


def test_recent_generated_paper_never_becomes_current_learning_position(tmp_path: Path):
    vault = tmp_path / "vault"
    concept = vault / "知识" / "张量与线性代数.md"
    paper = vault / "论文" / "自动生成论文.md"
    write_note(
        concept,
        note_type="concept",
        fields={"status": "未学"},
        body="- [x] 能说明 NCHW\n- [ ] 能定位维度错误",
    )
    write_note(paper, note_type="paper", fields={"status": "已精读"})
    os.utime(paper, (concept.stat().st_mtime + 100, concept.stat().st_mtime + 100))
    project_status = tmp_path / "STATUS.md"
    output = vault / "00_首页" / "学习状态.md"
    write_project_status(project_status)

    result = run_study_status(vault, project_status, output)

    assert result["current"] is None
    assert result["suggested"]["title"] == "张量与线性代数"
    assert "未明确选择" in output.read_text(encoding="utf-8")
    assert "- 最后修改：" not in output.read_text(encoding="utf-8")


def test_explicit_learning_status_is_the_only_current_position(tmp_path: Path):
    vault = tmp_path / "vault"
    write_note(
        vault / "知识" / "卷积运算.md",
        note_type="concept",
        fields={"status": "学习中"},
        body="- [x] 能解释权重共享\n- [ ] 能手算输出形状",
    )
    write_note(
        vault / "论文" / "LeNet.md",
        note_type="paper",
        fields={"study_status": "未学", "material_status": "双稿已完成"},
    )
    project_status = tmp_path / "STATUS.md"
    output = vault / "00_首页" / "学习状态.md"
    write_project_status(project_status)

    result = run_study_status(vault, project_status, output)

    assert result["current"]["title"] == "卷积运算"
    assert result["current"]["next_item"] == "能手算输出形状"


def test_paper_material_and_mastery_are_counted_separately(tmp_path: Path):
    vault = tmp_path / "vault"
    write_note(
        vault / "论文" / "LeNet.md",
        note_type="paper",
        fields={"study_status": "未学", "material_status": "双稿已完成"},
    )
    write_note(
        vault / "论文" / "ResNet.md",
        note_type="paper",
        fields={"study_status": "未学", "material_status": "原文已就绪"},
    )
    project_status = tmp_path / "STATUS.md"
    output = vault / "00_首页" / "学习状态.md"
    write_project_status(project_status)

    result = run_study_status(vault, project_status, output)
    text = output.read_text(encoding="utf-8")

    assert result["study_counts"]["paper"] == {"未学": 2}
    assert result["material_counts"] == {"原文已就绪": 1, "双稿已完成": 1}
    assert "资料准备不等于掌握" in text
    assert "双稿已完成" in text
    assert "未学" in text
