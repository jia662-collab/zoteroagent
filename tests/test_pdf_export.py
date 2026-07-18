from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / ".paperlab" / "paperlab.py"


def load_engine_module():
    spec = importlib.util.spec_from_file_location("paperlab_engine", ENGINE)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


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

<!-- PAPERLAB:TRANSLATION {"mode":"bilingual_sentence_aligned","source_units":2,"translated_units":2,"omitted_units":0} -->

## 1. 引言（Introduction）

### 原文 PDF 第 1 页｜Introduction

#### 原文 P001-001

This is the first complete source unit.

#### 译文 P001-001

这是第一个完整的原文单元。

#### 原文 P001-002

This is the second complete source unit.

#### 译文 P001-002

这是第二个完整的原文单元，按照原论文顺序翻译。

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


def test_export_preserves_verified_links_to_local_companion_pdfs(tmp_path: Path):
    companion = tmp_path / "中文全文对照.pdf"
    companion.write_bytes(b"existing companion")
    source = tmp_path / "reading.md"
    source.write_text(
        "# 学习入口\n\n[打开中文全文对照 PDF](中文全文对照.pdf)\n",
        encoding="utf-8",
    )
    output = tmp_path / "reading.pdf"

    run_engine("export", "--input", source, "--output", output, "--kind", "learning")

    with fitz.open(output) as document:
        links = [link.get("file", "") for page in document for link in page.get_links()]
    assert any(path.endswith("%E5%AF%B9%E7%85%A7.pdf") for path in links)


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


def test_export_rejects_summary_mislabeled_as_full_translation(tmp_path: Path):
    source = tmp_path / "summary.md"
    source.write_text(
        """# 中文全文对照版

> 原文：Example Paper｜原文 PDF 第 1-3 页
>
> 机器辅助翻译，原文为准。

## 概要

这是经过概括和删减的中文摘要，不是逐句全文翻译。
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
            str(tmp_path / "summary.pdf"),
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


def test_export_accepts_complete_translation_with_main_and_supplement_page_anchors(tmp_path: Path):
    source = tmp_path / "multi-source.md"
    source.write_text(
        """# 中文全文对照版

> 机器辅助翻译，原文为准。

<!-- PAPERLAB:TRANSLATION {"mode":"bilingual_sentence_aligned","source_units":2,"translated_units":2,"omitted_units":0} -->

## 主文 PDF 第 1 页

#### 原文 MAIN-P001-001

Main paper text.

#### 译文 MAIN-P001-001

主文正文。

## 补充材料 PDF 第 1 页

#### 原文 SUPP-P001-001

Supplementary text.

#### 译文 SUPP-P001-001

补充材料正文。
""",
        encoding="utf-8",
    )

    result = run_engine(
        "export",
        "--input",
        source,
        "--output",
        tmp_path / "multi-source.pdf",
        "--kind",
        "translation",
    )

    assert result["status"] == "created"


def test_export_renders_bracket_display_math_instead_of_printing_latex(tmp_path: Path):
    source = tmp_path / "math.md"
    source.write_text(
        r"""# 精读学习版

\[
L=\frac{1}{N}\sum_{i=1}^{N}x_i.
\tag{1}
\]
""",
        encoding="utf-8",
    )
    output = tmp_path / "math.pdf"

    run_engine("export", "--input", source, "--output", output, "--kind", "learning")

    with fitz.open(output) as document:
        text = "\n".join(page.get_text() for page in document)
    assert r"\frac" not in text
    assert r"\sum" not in text
    assert "(1)" in text


def test_markdown_document_uses_approved_publisher_bilingual_layout(tmp_path: Path):
    source = tmp_path / "publisher.md"
    source.write_text(
        """# 出版式双语稿

#### 原文 P001-001

English source paragraph.

#### 译文 P001-001

中文完整译文。
""",
        encoding="utf-8",
    )

    rendered = load_engine_module().markdown_document(source, "translation")

    assert 'class="bilingual-pair"' in rendered
    assert 'class="source-text"' in rendered
    assert 'class="translation-text"' in rendered
    assert 'font-family: Georgia' in rendered
    assert 'font-family: "SimSun"' in rendered
    assert ".translation pre code" in rendered
    assert re.search(r"\.translation-text\s*\{[^}]*break-inside:\s*avoid", rendered, flags=re.S)
    assert re.search(r"\.pair-label\s*\{[^}]*break-after:\s*avoid", rendered, flags=re.S)


def test_inline_math_keeps_chinese_prose_and_currency_outside_formula_images():
    engine = load_engine_module()
    source = r"输入 $256\times256$ 区域；输出 $224\times224$。paid $5 and $10."

    prepared, fragments = engine._prepare_math(source)

    assert "区域；输出" in prepared
    assert "paid $5 and $10" in prepared
    assert len(fragments) == 2
    assert all("区域；输出" not in fragment for fragment in fragments.values())


def test_export_adds_a_page_number_footer(tmp_path: Path):
    source = tmp_path / "numbered.md"
    source.write_text("# Publisher Proof\n\nBody without digits.\n", encoding="utf-8")
    output = tmp_path / "numbered.pdf"

    run_engine("export", "--input", source, "--output", output, "--kind", "learning")

    with fitz.open(output) as document:
        page = document[0]
        blocks = page.get_text("blocks")
        header = next(block for block in blocks if "GUIDED READING EDITION" in block[4])
        footer = next(block for block in blocks if block[4].strip() == "1")
        assert header[1] < 40
        assert footer[1] > page.rect.height - 40


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
