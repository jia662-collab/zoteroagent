from __future__ import annotations

import hashlib
import json
import runpy
import subprocess
import sys
from pathlib import Path

import fitz
import pytest


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


def test_export_renders_latex_math_instead_of_printing_source_markers(tmp_path: Path):
    source = tmp_path / "math.md"
    source.write_text(
        r"""# 精读学习版

行内公式 $a_i=x_i^2$ 应正常排版。

$$
L=\frac{1}{N}\sum_{i=1}^{N}x_i. \tag{1}
$$
""",
        encoding="utf-8",
    )
    output = tmp_path / "math.pdf"

    run_engine(
        "export",
        "--input",
        source,
        "--output",
        output,
        "--kind",
        "learning",
    )

    with fitz.open(output) as document:
        text = "\n".join(page.get_text() for page in document)

    assert "应正常排版" in text
    assert "\\frac" not in text
    assert "\\sum" not in text
    assert "$$" not in text
    assert "(1)" in text


def test_requirements_include_matplotlib_math_renderer():
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")

    assert "matplotlib" in requirements.casefold()


def test_prepare_math_preserves_currency_amounts():
    engine = runpy.run_path(str(ENGINE))

    text, fragments = engine["_prepare_math"]("paid $5 and $10")

    assert text == "paid $5 and $10"
    assert fragments == {}


def test_prepare_math_still_renders_numeric_display_equation():
    engine = runpy.run_path(str(ENGINE))

    text, fragments = engine["_prepare_math"]("$$5$$")

    assert "$$" not in text
    assert len(fragments) == 1


def test_export_allows_literal_latex_in_inline_code(tmp_path: Path):
    source = tmp_path / "literal.md"
    source.write_text("# Learning\n\nLiteral example: `\\frac{1}{N}`.\n", encoding="utf-8")
    output = tmp_path / "literal.pdf"

    run_engine("export", "--input", source, "--output", output, "--kind", "learning")

    with fitz.open(output) as document:
        text = "\n".join(page.get_text() for page in document)
    assert r"\frac{1}{N}" in text


def test_export_renders_display_math_inside_blockquote(tmp_path: Path):
    source = tmp_path / "quoted-math.md"
    source.write_text(
        r"""# Learning

> $$
> L=\frac{1}{N}\sum_{i=1}^{N}x_i.
> $$
""",
        encoding="utf-8",
    )
    output = tmp_path / "quoted-math.pdf"

    run_engine("export", "--input", source, "--output", output, "--kind", "learning")

    with fitz.open(output) as document:
        text = "\n".join(page.get_text() for page in document)
    assert r"\frac" not in text
    assert r"\sum" not in text
    assert "$$" not in text


def test_pdf_validation_rejects_raw_latex_source(tmp_path: Path):
    pdf = tmp_path / "broken.pdf"
    document = fitz.open()
    document.new_page().insert_text((72, 72), r"L=\frac{1}{N}")
    document.save(pdf)
    document.close()
    engine = runpy.run_path(str(ENGINE))

    with pytest.raises(engine["PaperLabError"]) as error:
        engine["validate_exported_pdf"](pdf)

    assert error.value.code == "export_validation_failed"


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
