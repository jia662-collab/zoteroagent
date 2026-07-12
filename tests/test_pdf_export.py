from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / ".paperlab" / "paperlab.py"


def run_engine(*args: object) -> dict:
    completed = subprocess.run(
        [sys.executable, str(ENGINE), *(str(value) for value in args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    return json.loads(completed.stdout)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_export_creates_chinese_pdf_with_source_anchors_and_image(tmp_path: Path):
    image = tmp_path / "figure.png"
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 120, 80), False)
    pixmap.clear_with(0xF0F0F0)
    pixmap.save(image)

    source = tmp_path / "paper.md"
    source.write_text(
        """# 中文全文对照版

> 原文：Example Paper｜原文 PDF 第 1-3 页
>
> 机器辅助翻译，原文为准。

## 1. 引言（Introduction）

这不是摘要，而是按照原论文顺序翻译和解释的中文正文。

![图 1：原论文第 2 页](figure.png)

<!-- hidden workflow metadata -->
""",
        encoding="utf-8",
    )
    before = sha256(source)
    output = tmp_path / "paper_中文全文对照.pdf"

    result = run_engine(
        "export",
        "--input",
        source,
        "--output",
        output,
        "--kind",
        "translation",
    )

    document = fitz.open(output)
    text = "\n".join(page.get_text() for page in document)
    images = sum(len(page.get_images(full=True)) for page in document)
    document.close()

    assert result["status"] == "created"
    assert result["kind"] == "translation"
    assert result["pages"] >= 1
    assert "中文全文对照版" in text
    assert "原文 PDF 第 1-3 页" in text
    assert "按照原论文顺序" in text
    assert "hidden workflow metadata" not in text
    assert images >= 1
    assert sha256(source) == before


def test_export_refuses_to_overwrite_without_explicit_replace(tmp_path: Path):
    source = tmp_path / "reading.md"
    source.write_text("# 精读学习版\n\n沿作者论证顺序学习。\n", encoding="utf-8")
    output = tmp_path / "reading.pdf"
    output.write_bytes(b"keep")

    completed = subprocess.run(
        [
            sys.executable,
            str(ENGINE),
            "export",
            "--input",
            str(source),
            "--output",
            str(output),
            "--kind",
            "learning",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
    )

    assert completed.returncode == 2
    assert json.loads(completed.stdout)["error"] == "output_exists"
    assert output.read_bytes() == b"keep"


def test_export_replace_is_atomic_and_reports_new_document(tmp_path: Path):
    source = tmp_path / "reading.md"
    source.write_text("# 精读学习版\n\n新的递进讲解。\n", encoding="utf-8")
    output = tmp_path / "reading.pdf"
    output.write_bytes(b"old")

    result = run_engine(
        "export",
        "--input",
        source,
        "--output",
        output,
        "--kind",
        "learning",
        "--replace",
    )

    assert result["status"] == "replaced"
    with fitz.open(output) as document:
        assert "新的递进讲解" in "\n".join(page.get_text() for page in document)
    assert not list(tmp_path.glob("*.tmp"))


def test_export_rejects_translation_without_source_alignment(tmp_path: Path):
    source = tmp_path / "translation.md"
    source.write_text("# 中文全文对照版\n\n只有概括，没有来源定位。\n", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(ENGINE),
            "export",
            "--input",
            str(source),
            "--output",
            str(tmp_path / "translation.pdf"),
            "--kind",
            "translation",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
    )

    assert completed.returncode == 2
    assert json.loads(completed.stdout)["error"] == "invalid_translation"


def test_export_rejects_legacy_cross_cut_reading_structure(tmp_path: Path):
    source = tmp_path / "legacy.md"
    source.write_text(
        """# 精读

### 一页读懂
概括。
### 问题与直觉
问题。
### 方法如何运作
方法。
### 结果如何解释
结果。
### 贡献、边界与下一步
贡献。
""",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(ENGINE),
            "export",
            "--input",
            str(source),
            "--output",
            str(tmp_path / "legacy.pdf"),
            "--kind",
            "learning",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
    )

    assert completed.returncode == 2
    assert json.loads(completed.stdout)["error"] == "legacy_reading_structure"
