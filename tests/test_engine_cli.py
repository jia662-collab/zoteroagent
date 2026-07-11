from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import fitz


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


def test_read_caps_pages_and_characters_without_modifying_pdf(tmp_path: Path):
    pdf = tmp_path / "long.pdf"
    doc = fitz.open()
    for page_number in range(12):
        page = doc.new_page()
        page.insert_text((72, 72), f"page {page_number + 1} " + ("evidence " * 700))
    doc.save(pdf)
    doc.close()
    before = sha256(pdf)

    result = run_engine("read", "--pdf", pdf, "--cache-dir", tmp_path / "cache")
    assert result["status"] == "ok"
    assert len(result["pages"]) <= 8
    assert sum(len(page["text"]) for page in result["pages"]) <= 20_000
    assert result["truncated"] is True
    assert sha256(pdf) == before


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
