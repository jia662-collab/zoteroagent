from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from pypdf import PdfWriter


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / ".paperlab" / "paperlab.py"


def run_process(*args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ENGINE), *(str(arg) for arg in args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
    )


def run_engine(*args: object) -> dict:
    cp = run_process(*args)
    assert cp.returncode == 0, cp.stdout + cp.stderr
    return json.loads(cp.stdout)


def git(repo: Path, *args: str) -> str:
    cp = subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, encoding="utf-8")
    assert cp.returncode == 0, cp.stdout + cp.stderr
    return cp.stdout.strip()


def init_private_repo(tmp_path: Path) -> tuple[Path, str]:
    data = tmp_path / "research"
    project = run_engine("init", "--data-root", data, "--title", "长期课题", "--goal", "持续积累证据")
    git(data, "init", "-b", "main")
    return data, project["project_id"]


def test_checkpoint_creates_local_private_commit(tmp_path: Path):
    data, project_id = init_private_repo(tmp_path)
    result = run_engine(
        "checkpoint",
        "--data-root",
        data,
        "--project",
        project_id,
        "--stage",
        "screening",
        "--completed",
        "selection",
        "--next",
        "筛选已导入论文",
        "--backup",
        "--no-push",
    )

    assert result["backup"]["status"] == "local_commit"
    assert git(data, "log", "-1", "--pretty=%s") == f"research({project_id}): checkpoint screening"
    assert git(data, "status", "--short") == ""
    assert (data / ".gitignore").read_text(encoding="utf-8").splitlines()[:2] == ["*.pdf", "*.bib"]


def test_backup_rejects_sensitive_staged_content(tmp_path: Path):
    data, project_id = init_private_repo(tmp_path)
    pdf = data / "projects" / project_id / "secret.pdf"
    pdf.write_bytes(b"private paper")
    git(data, "add", "-f", str(pdf.relative_to(data)))

    cp = run_process(
        "checkpoint",
        "--data-root",
        data,
        "--project",
        project_id,
        "--stage",
        "reading",
        "--next",
        "精读",
        "--backup",
        "--no-push",
    )
    assert cp.returncode == 2
    assert json.loads(cp.stdout)["error"] == "sensitive_backup_content"
    assert not (data / ".git" / "refs" / "heads" / "main").exists()


def test_backup_rejects_local_figure_assets(tmp_path: Path):
    data, project_id = init_private_repo(tmp_path)
    asset = data / "projects" / project_id / "assets" / "paper" / "figure-01.png"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"derived figure")
    assert "**/assets/" in (data / ".gitignore").read_text(encoding="utf-8").splitlines()
    git(data, "add", "-f", str(asset.relative_to(data)))

    cp = run_process(
        "checkpoint",
        "--data-root",
        data,
        "--project",
        project_id,
        "--stage",
        "reading",
        "--next",
        "继续精读",
        "--backup",
        "--no-push",
    )

    assert cp.returncode == 2
    assert json.loads(cp.stdout)["error"] == "sensitive_backup_content"


def test_backup_rejects_zotero_storage_path_in_staged_text(tmp_path: Path):
    data, project_id = init_private_repo(tmp_path)
    note = data / "projects" / project_id / "papers" / "unsafe.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    zotero_path = "C:" + r"\Users\Researcher\Zotero\storage\ABCD1234\paper.pdf"
    note.write_text(
        f"附件：{zotero_path}",
        encoding="utf-8",
    )
    git(data, "add", str(note.relative_to(data)))

    cp = run_process(
        "checkpoint",
        "--data-root",
        data,
        "--project",
        project_id,
        "--stage",
        "reading",
        "--next",
        "精读",
        "--backup",
        "--no-push",
    )

    assert cp.returncode == 2
    assert json.loads(cp.stdout)["error"] == "sensitive_backup_content"
    assert not (data / ".git" / "refs" / "heads" / "main").exists()


def test_backup_scans_large_text_and_forward_slash_zotero_paths(tmp_path: Path):
    data, project_id = init_private_repo(tmp_path)
    note = data / "projects" / project_id / "papers" / "large-unsafe.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text(
        ("research notes\n" * 150_000) + "附件：C:/Users/Researcher/Zotero/storage/ABCD1234/paper.pdf\n",
        encoding="utf-8",
    )
    assert note.stat().st_size > 2_000_000
    git(data, "add", str(note.relative_to(data)))

    cp = run_process(
        "checkpoint",
        "--data-root",
        data,
        "--project",
        project_id,
        "--stage",
        "reading",
        "--next",
        "精读",
        "--backup",
        "--no-push",
    )

    assert cp.returncode == 2
    assert json.loads(cp.stdout)["error"] == "sensitive_backup_content"


def test_pending_push_is_retried_at_next_checkpoint(tmp_path: Path):
    data, project_id = init_private_repo(tmp_path)
    git(data, "remote", "add", "origin", str(tmp_path / "offline" / "missing.git"))

    first = run_engine(
        "checkpoint",
        "--data-root",
        data,
        "--project",
        project_id,
        "--stage",
        "screening",
        "--next",
        "继续筛选",
        "--backup",
    )
    assert first["backup"]["status"] == "pending_push"
    state = json.loads((data / "state" / f"{project_id}.json").read_text(encoding="utf-8"))
    assert state["backup_status"] == "pending_push"

    remote = tmp_path / "remote.git"
    cp = subprocess.run(
        ["git", "init", "--bare", str(remote)],
        text=True,
        capture_output=True,
        encoding="utf-8",
    )
    assert cp.returncode == 0, cp.stdout + cp.stderr
    git(data, "remote", "set-url", "origin", str(remote))

    second = run_engine(
        "checkpoint",
        "--data-root",
        data,
        "--project",
        project_id,
        "--stage",
        "screening",
        "--next",
        "继续筛选",
        "--backup",
    )
    assert second["backup"]["status"] == "synced"
    assert run_engine("status", "--data-root", data, "--project", project_id)["backup_status"] == "synced"
    assert git(data, "status", "--short") == ""
    assert git(remote, "rev-parse", "main") == git(data, "rev-parse", "HEAD")


def test_status_detects_commit_not_present_on_remote(tmp_path: Path):
    data, project_id = init_private_repo(tmp_path)
    run_engine(
        "checkpoint",
        "--data-root",
        data,
        "--project",
        project_id,
        "--stage",
        "screening",
        "--next",
        "继续筛选",
        "--backup",
        "--no-push",
    )
    state_path = data / "state" / f"{project_id}.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["backup_status"] = "synced"
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    git(data, "add", str(state_path.relative_to(data)))
    git(
        data,
        "-c",
        "user.name=PaperLab",
        "-c",
        "user.email=paperlab@localhost",
        "commit",
        "-m",
        "simulate interrupted push",
    )

    result = run_engine("status", "--data-root", data, "--project", project_id)

    assert result["backup_status"] == "pending_push"
    persisted = json.loads(state_path.read_text(encoding="utf-8"))
    assert persisted["backup_status"] == "pending_push"


def test_backup_lock_prevents_simultaneous_git_operation(tmp_path: Path):
    data, project_id = init_private_repo(tmp_path)
    (data / ".paperlab" / "backup.lock").mkdir(parents=True)

    cp = run_process(
        "checkpoint",
        "--data-root",
        data,
        "--project",
        project_id,
        "--stage",
        "reading",
        "--next",
        "精读",
        "--backup",
        "--no-push",
    )
    assert cp.returncode == 2
    assert json.loads(cp.stdout)["error"] == "backup_busy"


def test_doctor_reports_local_readiness(tmp_path: Path):
    data, _ = init_private_repo(tmp_path)
    bib = tmp_path / "library.bib"
    bib.write_text("@article{x, title={X}, year={2025}}\n", encoding="utf-8")

    result = run_engine("doctor", "--data-root", data, "--bibtex", bib)
    assert result["ready"] is True
    assert result["checks"]["private_git_repo"] is True
    assert result["checks"]["bibtex_entries"] == 1
    assert result["checks"]["pymupdf"] is True
    assert result["checks"]["pypdf"] is True
    assert result["checks"]["markdown"] is True
    assert Path(result["checks"]["pdf_browser"]).name.lower() in {"msedge.exe", "chrome.exe", "chromium.exe"}


def test_encrypted_pdf_is_reported_without_text(tmp_path: Path):
    pdf = tmp_path / "encrypted.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    writer.encrypt("secret")
    with pdf.open("wb") as handle:
        writer.write(handle)

    result = run_engine("read", "--pdf", pdf, "--cache-dir", tmp_path / "cache")
    assert result["status"] == "encrypted"
    assert result["pages"] == []


def test_public_repository_ignores_private_research_and_local_sources():
    rules = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "research/" in rules
    assert "bibliography/library.bib" in rules
    assert ".paperlab/cache/" in rules
    assert "*.pdf" in rules
