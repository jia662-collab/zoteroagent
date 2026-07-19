from __future__ import annotations

import errno
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import fitz
import pytest


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / ".paperlab" / "paperlab.py"


def run_engine(*args: object, cwd: Path = ROOT) -> dict:
    cp = subprocess.run(
        [sys.executable, str(ENGINE), *(str(arg) for arg in args)],
        cwd=cwd,
        text=True,
        capture_output=True,
        encoding="utf-8",
    )
    assert cp.returncode == 0, cp.stdout + cp.stderr
    return json.loads(cp.stdout)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_projects_keep_independent_recoverable_state(tmp_path: Path):
    data = tmp_path / "research"
    first = run_engine("init", "--data-root", data, "--title", "柔性量子点探测器", "--goal", "比较关键方法")
    second = run_engine("init", "--data-root", data, "--title", "数字金融风险", "--goal", "梳理理论证据")

    run_engine(
        "checkpoint",
        "--data-root",
        data,
        "--project",
        first["project_id"],
        "--stage",
        "selection",
        "--completed",
        "discovery",
        "--next",
        "选择候选论文",
        "--selected",
        "paper-a,paper-b",
    )

    first_status = run_engine("status", "--data-root", data, "--project", first["project_id"])
    second_status = run_engine("status", "--data-root", data, "--project", second["project_id"])
    assert first_status["stage"] == "selection"
    assert first_status["selected_citation_keys"] == ["paper-a", "paper-b"]
    assert second_status["stage"] == "discovery"
    assert second_status["selected_citation_keys"] == []
    assert (data / "projects" / first["project_id"] / "STATUS.md").stat().st_size <= 2048
    assert not list(data.rglob("*.tmp"))


def test_project_description_budget_is_enforced(tmp_path: Path):
    cp = subprocess.run(
        [
            sys.executable,
            str(ENGINE),
            "init",
            "--data-root",
            str(tmp_path / "research"),
            "--title",
            "过长项目",
            "--goal",
            "研" * 5000,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
    )
    assert cp.returncode == 2
    payload = json.loads(cp.stdout)
    assert payload["error"] == "project_budget_exceeded"


def test_sync_uses_current_bibtex_instead_of_stale_index(tmp_path: Path):
    bib = tmp_path / "library.bib"
    index = tmp_path / "library.json"
    zotero_path = "C:" + r"\Users\Researcher\Zotero\storage\ABCD1234\paper.pdf"
    bib.write_text(
        f"""@article{{zhang2025,
  title = {{中文与 English 标题}},
  author = {{Zhang, San and Li, Si}},
  year = {{2025}},
  doi = {{https://doi.org/10.1000/ABC.1}},
  file = {{{zotero_path}}}
}}\n""",
        encoding="utf-8",
    )
    index.write_text("[]\n", encoding="utf-8")

    result = run_engine("sync", "--bibtex", bib, "--index", index)
    records = json.loads(index.read_text(encoding="utf-8"))
    assert result["entry_count"] == 1
    assert records[0]["citation_key"] == "zhang2025"
    assert records[0]["doi"] == "10.1000/abc.1"
    assert records[0]["file"][0].endswith("paper.pdf")


def test_read_returns_all_requested_pages_without_fixed_limits(tmp_path: Path):
    pdf = tmp_path / "long.pdf"
    doc = fitz.open()
    for page_number in range(12):
        page = doc.new_page()
        for line_number in range(80):
            page.insert_text(
                (36, 36 + line_number * 8),
                f"page {page_number + 1} line {line_number + 1} " + ("evidence " * 9),
                fontsize=6,
            )
    doc.save(pdf)
    doc.close()
    before = sha256(pdf)

    result = run_engine("read", "--pdf", pdf, "--cache-dir", tmp_path / "cache")
    assert result["status"] == "ok"
    assert len(result["pages"]) == 12
    assert sum(len(page["text"]) for page in result["pages"]) > 20_000
    assert result["truncated"] is False
    assert sha256(pdf) == before


def test_read_outline_detects_sections_and_reference_boundary(tmp_path: Path):
    pdf = tmp_path / "structured.pdf"
    doc = fitz.open()
    for text in [
        "1 Introduction\nResearch motivation",
        "3 connected to normalized outputs from an earlier layer\nBackground details",
        "2\nMethods\nExperimental design",
        "References\n[1] Example citation",
        "[2] Another citation",
    ]:
        page = doc.new_page()
        page.insert_textbox(fitz.Rect(72, 72, 520, 760), text, fontsize=14)
    doc.save(pdf)
    doc.close()

    result = run_engine("read", "--pdf", pdf, "--cache-dir", tmp_path / "cache", "--outline")

    assert result["status"] == "ok"
    assert result["references_start"] == 4
    assert [(section["title"], section["start_page"], section["end_page"]) for section in result["sections"]] == [
        ("Introduction", 1, 2),
        ("Methods", 3, 3),
    ]
    assert all(section["source"] == "heuristic" for section in result["sections"])


def test_read_outline_finds_reference_boundary_missing_from_pdf_toc(tmp_path: Path):
    pdf = tmp_path / "toc-without-references.pdf"
    doc = fitz.open()
    for text in [
        "1 Introduction\n" + "Motivation and background evidence. " * 4,
        "2 Methods\n" + "Experimental design and procedure. " * 4,
        "References\n[1] Example citation with complete metadata",
    ]:
        page = doc.new_page()
        page.insert_textbox(fitz.Rect(72, 72, 520, 760), text, fontsize=14)
    doc.set_toc([[1, "1 Introduction", 1], [1, "2 Methods", 2]])
    doc.save(pdf)
    doc.close()

    result = run_engine("read", "--pdf", pdf, "--cache-dir", tmp_path / "cache", "--outline")

    assert result["references_start"] == 3
    assert result["sections"][-1]["end_page"] == 2
    assert all(section["source"] == "toc" for section in result["sections"])


def test_read_outline_preserves_body_before_numbered_references_on_same_page(tmp_path: Path):
    pdf = tmp_path / "same-page-references.pdf"
    doc = fitz.open()
    for text in [
        "1 Introduction\n" + "Background evidence. " * 8,
        "2 Methods\nMethod details remain on this page.\n3 References\n[1] Citation",
    ]:
        page = doc.new_page()
        page.insert_textbox(fitz.Rect(72, 72, 520, 760), text, fontsize=14)
    doc.save(pdf)
    doc.close()

    result = run_engine("read", "--pdf", pdf, "--cache-dir", tmp_path / "cache", "--outline")

    assert result["references_start"] == 2
    assert result["sections"][-1]["title"] == "Methods"
    assert result["sections"][-1]["end_page"] == 2


def test_read_outline_keeps_same_page_toc_sections_readable(tmp_path: Path):
    pdf = tmp_path / "same-page-toc-sections.pdf"
    doc = fitz.open()
    for text in [
        "1 Introduction\n2 Methods\n" + "Shared page content. " * 8,
        "3 Results\n" + "Result evidence. " * 8,
    ]:
        page = doc.new_page()
        page.insert_textbox(fitz.Rect(72, 72, 520, 760), text, fontsize=14)
    doc.set_toc([[1, "1 Introduction", 1], [1, "2 Methods", 1], [1, "3 Results", 2]])
    doc.save(pdf)
    doc.close()

    result = run_engine("read", "--pdf", pdf, "--cache-dir", tmp_path / "cache", "--outline")

    assert [(section["start_page"], section["end_page"]) for section in result["sections"]] == [(1, 1), (1, 1), (2, 2)]


def test_read_outline_keeps_body_when_toc_references_share_its_page(tmp_path: Path):
    pdf = tmp_path / "toc-reference-same-page.pdf"
    doc = fitz.open()
    for text in [
        "1 Introduction\n" + "Background evidence. " * 8,
        "2 Conclusion\nFinal body text remains readable.\nReferences\n[1] Citation",
    ]:
        page = doc.new_page()
        page.insert_textbox(fitz.Rect(72, 72, 520, 760), text, fontsize=14)
    doc.set_toc([[1, "1 Introduction", 1], [1, "2 Conclusion", 2], [1, "References", 2]])
    doc.save(pdf)
    doc.close()

    result = run_engine("read", "--pdf", pdf, "--cache-dir", tmp_path / "cache", "--outline")

    assert result["references_start"] == 2
    assert result["sections"][-1]["start_page"] == 2
    assert result["sections"][-1]["end_page"] == 2


def test_sync_reports_candidate_zotero_and_pdf_readiness(tmp_path: Path):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"pdf placeholder")
    bib = tmp_path / "library.bib"
    index = tmp_path / "library.json"
    escaped_pdf = str(pdf).replace("\\", "\\\\")
    bib.write_text(
        f"""@article{{noFile,
  title = {{Duplicate DOI without attachment}},
  doi = {{10.1000/duplicate}}
}}
@article{{withFile,
  title = {{Duplicate DOI with attachment}},
  doi = {{10.1000/duplicate}},
  file = {{{escaped_pdf}}}
}}
@article{{titleOnly,
  title = {{Exact Title Match}},
  file = {{{escaped_pdf}}}
}}
@article{{doiOnly,
  title = {{Shared Duplicate Title}},
  doi = {{10.1000/shared}}
}}
@article{{attachmentOnly,
  title = {{Shared Duplicate Title}},
  file = {{{escaped_pdf}}}
}}
@article{{alpha,
  title = {{α-Synuclein Aggregation}}
}}
@article{{beta,
  title = {{β-Synuclein Aggregation}},
  file = {{{escaped_pdf}}}
}}
""",
        encoding="utf-8",
    )
    candidates = tmp_path / "candidates.json"
    candidates.write_text(
        json.dumps(
            [
                {"id": 1, "title": "DOI candidate", "doi": "https://doi.org/10.1000/DUPLICATE"},
                {"id": 2, "title": "Exact Title Match"},
                {"id": 3, "title": "Not in Zotero"},
                {"id": 4, "title": "Shared Duplicate Title", "doi": "10.1000/shared"},
                {"id": 5, "title": "α-Synuclein Aggregation"},
            ]
        ),
        encoding="utf-8",
    )

    result = run_engine("sync", "--bibtex", bib, "--index", index, "--candidates", candidates)

    assert result["readiness"] == {
        "candidate_count": 5,
        "matched": 4,
        "ready": 3,
        "missing_pdf": 1,
        "not_in_zotero": 1,
    }
    doi_match = result["matches"][0]
    assert doi_match["matched_by"] == "doi"
    assert doi_match["citation_key"] == "withFile"
    assert doi_match["pdf_count"] == 1
    assert doi_match["duplicate_keys"] == ["noFile", "withFile"]
    assert result["matches"][1]["matched_by"] == "title"
    assert result["matches"][2]["status"] == "not_in_zotero"
    shared = result["matches"][3]
    assert shared["matched_by"] == "doi"
    assert shared["citation_key"] == "attachmentOnly"
    assert shared["status"] == "ready"
    assert shared["duplicate_keys"] == ["doiOnly", "attachmentOnly"]
    assert result["matches"][4]["citation_key"] == "alpha"
    assert result["matches"][4]["status"] == "missing_pdf"


def test_render_creates_clipped_png_without_modifying_pdf(tmp_path: Path):
    pdf = tmp_path / "figure.pdf"
    doc = fitz.open()
    page = doc.new_page(width=400, height=300)
    page.draw_rect(fitz.Rect(20, 20, 380, 280), color=(0, 0, 0), fill=(1, 1, 1))
    page.insert_text((60, 100), "Figure 1", fontsize=24)
    doc.save(pdf)
    doc.close()
    before = sha256(pdf)
    output = tmp_path / "figure.png"

    result = run_engine(
        "render",
        "--pdf",
        pdf,
        "--page",
        1,
        "--clip",
        "0,0,0.5,1",
        "--output",
        output,
    )

    image = fitz.Pixmap(str(output))
    assert result["status"] == "created"
    assert result["page"] == 1
    assert result["clip"] == [0.0, 0.0, 0.5, 1.0]
    assert image.width == 500
    assert image.height == 750
    assert sha256(pdf) == before


def test_inspect_suggests_figure_crop_above_caption(tmp_path: Path):
    pdf = tmp_path / "figure-layout.pdf"
    doc = fitz.open()
    page = doc.new_page(width=600, height=800)
    page.insert_text((60, 40), "As shown in Figure 1, the model has several layers.", fontsize=10)
    page.draw_rect(fitz.Rect(80, 80, 520, 330), color=(0, 0, 0))
    page.insert_text((100, 370), "Figure 1: Model architecture", fontsize=14)
    doc.save(pdf)
    doc.close()

    result = run_engine("inspect", "--pdf", pdf, "--page", 1, "--label", "Figure 1")

    assert len(result["matches"]) == 1
    match = result["matches"][0]
    assert match["direction"] == "above"
    assert match["confidence"] == "high"
    assert match["object_count"] >= 1
    assert match["suggested_clip"] != [0.0, 0.0, 1.0, 1.0]
    assert match["suggested_clip"][0] <= 80 / 600
    assert match["suggested_clip"][2] >= 520 / 600


def test_inspect_suggests_table_crop_below_caption(tmp_path: Path):
    pdf = tmp_path / "table-layout.pdf"
    doc = fitz.open()
    page = doc.new_page(width=600, height=800)
    page.insert_text((100, 100), "Table 1: Results", fontsize=14)
    for y in [130, 180, 230, 280]:
        page.draw_line(fitz.Point(80, y), fitz.Point(520, y), color=(0, 0, 0))
    for x in [80, 250, 400, 520]:
        page.draw_line(fitz.Point(x, 130), fitz.Point(x, 280), color=(0, 0, 0))
    doc.save(pdf)
    doc.close()

    result = run_engine("inspect", "--pdf", pdf, "--page", 1, "--label", "Table 1")

    match = result["matches"][0]
    assert match["direction"] == "below"
    assert match["confidence"] == "high"
    assert match["suggested_clip"][1] <= 100 / 800
    assert match["suggested_clip"][3] >= 280 / 800


def test_render_rejects_invalid_requests_and_overwrite(tmp_path: Path):
    pdf = tmp_path / "figure.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(pdf)
    doc.close()
    occupied = tmp_path / "occupied.png"
    occupied.write_bytes(b"keep me")

    cases = [
        (["--page", "2", "--output", tmp_path / "page.png"], "invalid_page"),
        (["--page", "1", "--clip", "0.8,0,0.2,1", "--output", tmp_path / "clip.png"], "invalid_clip"),
        (["--page", "1", "--output", tmp_path / "figure.jpg"], "invalid_output"),
        (["--page", "1", "--output", occupied], "output_exists"),
    ]
    for arguments, expected_error in cases:
        cp = subprocess.run(
            [sys.executable, str(ENGINE), "render", "--pdf", str(pdf), *(str(arg) for arg in arguments)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            encoding="utf-8",
        )
        assert cp.returncode == 2
        assert json.loads(cp.stdout)["error"] == expected_error

    assert occupied.read_bytes() == b"keep me"


def test_create_bytes_exclusive_falls_back_when_hard_links_are_unavailable(tmp_path: Path, monkeypatch):
    spec = importlib.util.spec_from_file_location("paperlab_engine_test", ENGINE)
    assert spec and spec.loader
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)
    output = tmp_path / "fallback.bin"

    def unavailable(*_args) -> None:
        raise OSError(errno.EPERM, "hard links unavailable")

    monkeypatch.setattr(engine.os, "link", unavailable)
    engine.create_bytes_exclusive(output, b"payload")

    assert output.read_bytes() == b"payload"
    with pytest.raises(FileExistsError):
        engine.create_bytes_exclusive(output, b"replacement")
    assert output.read_bytes() == b"payload"


def test_render_does_not_clobber_file_created_during_exclusive_write(tmp_path: Path):
    spec = importlib.util.spec_from_file_location("paperlab_engine_test", ENGINE)
    assert spec and spec.loader
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)
    pdf = tmp_path / "figure.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(pdf)
    doc.close()
    output = tmp_path / "race.png"
    original_write = engine.create_bytes_exclusive

    def create_competing_file(path: Path, content: bytes) -> None:
        path.write_bytes(b"competing writer")
        original_write(path, content)

    engine.create_bytes_exclusive = create_competing_file
    with pytest.raises(engine.PaperLabError) as error:
        engine.render_page(pdf, 1, output, None)

    assert error.value.code == "output_exists"
    assert output.read_bytes() == b"competing writer"


def test_read_rejects_invalid_page_specs(tmp_path: Path):
    pdf = tmp_path / "three-pages.pdf"
    doc = fitz.open()
    for page_number in range(3):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {page_number + 1} with enough extractable text for validation")
    doc.save(pdf)
    doc.close()

    for page_spec in ["0", "1-9", "3-2", "1,,2", "x"]:
        cp = subprocess.run(
            [sys.executable, str(ENGINE), "read", "--pdf", str(pdf), "--cache-dir", str(tmp_path / "cache"), "--pages", page_spec],
            cwd=ROOT,
            text=True,
            capture_output=True,
            encoding="utf-8",
        )
        assert cp.returncode == 2
        assert json.loads(cp.stdout)["error"] == "invalid_page_spec"


def test_read_reports_scanned_and_corrupt_pdf(tmp_path: Path):
    scanned = tmp_path / "scan.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(scanned)
    doc.close()
    corrupt = tmp_path / "corrupt.pdf"
    corrupt.write_bytes(b"not a pdf")

    scan_result = run_engine("read", "--pdf", scanned, "--cache-dir", tmp_path / "cache")
    corrupt_result = run_engine("read", "--pdf", corrupt, "--cache-dir", tmp_path / "cache")
    assert scan_result["status"] == "scanned_suspect"
    assert scan_result["pages"] == []
    assert corrupt_result["status"] == "corrupt"
    assert corrupt_result["pages"] == []


def test_ris_exports_only_selected_verified_unique_records(tmp_path: Path):
    candidates = tmp_path / "candidates.json"
    output = tmp_path / "zotero_import.ris"
    candidates.write_text(
        json.dumps(
            [
                {"id": 1, "title": "第一篇", "authors": ["张三", "李四"], "year": "2025", "doi": "10.1/a", "verification": "verified"},
                {"id": 2, "title": "未核验", "authors": ["王五"], "year": "2024", "verification": "unverified"},
                {"id": 3, "title": "重复版本", "authors": ["Zhang San"], "year": "2025", "doi": "https://doi.org/10.1/A", "verification": "verified"},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = run_engine("ris", "--input", candidates, "--ids", "1,2,3", "--output", output)
    text = output.read_text(encoding="utf-8")
    assert result == {"exported": 1, "rejected": [2], "duplicates": [3], "output": str(output.resolve())}
    assert text.count("TY  - JOUR") == 1
    assert "AU  - 张三" in text
    assert "DO  - 10.1/a" in text
