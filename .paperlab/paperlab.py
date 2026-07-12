from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
from datetime import date, datetime
from pathlib import Path
from typing import Any


PROJECT_BUDGET = 4096
STATUS_BUDGET = 2048


class PaperLabError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def normalize_doi(value: str | None) -> str:
    if not value:
        return ""
    result = value.strip()
    result = re.sub(r"^https?://(dx\.)?doi\.org/", "", result, flags=re.I)
    result = re.sub(r"^doi:\s*", "", result, flags=re.I)
    return result.strip().lower()


def normalize_title(value: str | None) -> str:
    if not value:
        return ""
    result = unicodedata.normalize("NFKC", re.sub(r"[{}]", "", value)).casefold()
    result = "".join(character if character.isalnum() else " " for character in result)
    return re.sub(r"\s+", " ", result).strip()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_json(path: Path, value: Any) -> None:
    atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def project_slug(title: str) -> str:
    result = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", title.strip())
    result = re.sub(r"\s+", "_", result)
    result = re.sub(r"_+", "_", result).strip("._")
    return (result or "research")[:48]


def project_paths(data_root: Path, project_id: str) -> dict[str, Path]:
    return {
        "project": data_root / "projects" / project_id,
        "state": data_root / "state" / f"{project_id}.json",
        "events": data_root / "events" / f"{project_id}.jsonl",
    }


def project_markdown(project_id: str, title: str, goal: str) -> str:
    return f"""# {title}

- 项目编号：`{project_id}`
- 语言：中文为主，保留必要英文术语

## 研究目标

{goal.strip()}

## 核心问题

- 待与研究过程共同明确。

## 纳入范围

- 待确认。

## 排除范围

- 待确认。

## 人工决策

- 本节只由用户或经用户确认后修改。
"""


def default_state(project_id: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "project_id": project_id,
        "stage": "discovery",
        "completed_steps": [],
        "pending_actions": [],
        "next_action": "搜索候选论文",
        "selected_citation_keys": [],
        "processed_citation_keys": [],
        "bibliography_fingerprint": "",
        "updated_at": now_iso(),
        "backup_status": "not_configured",
    }


def status_markdown(state: dict[str, Any]) -> str:
    completed = state.get("completed_steps") or []
    pending = state.get("pending_actions") or []
    text = "\n".join(
        [
            "# 当前进度",
            "",
            f"- 项目：`{state['project_id']}`",
            f"- 阶段：{state['stage']}",
            f"- 下一步：{state['next_action']}",
            f"- 已完成：{', '.join(completed[-8:]) or '无'}",
            f"- 待处理：{', '.join(pending[:5]) or '无'}",
            f"- 已选择论文：{len(state.get('selected_citation_keys') or [])}",
            f"- 已处理论文：{len(state.get('processed_citation_keys') or [])}",
            f"- 备份：{state.get('backup_status', 'unknown')}",
            f"- 更新时间：{state['updated_at']}",
            "",
            "> 此文件由 PaperLab 自动生成；研究目标请修改 PROJECT.md。",
            "",
        ]
    )
    encoded = text.encode("utf-8")
    if len(encoded) > STATUS_BUDGET:
        text = encoded[: STATUS_BUDGET - 4].decode("utf-8", errors="ignore") + "...\n"
    return text


def private_gitignore() -> str:
    return """*.pdf
*.bib
*.sqlite
.env
.env.*
cache/
**/cache/
**/assets/
*.log
.paperlab/
"""


def rebuild_index(data_root: Path) -> None:
    rows = []
    for state_path in sorted((data_root / "state").glob("*.json")):
        state = read_json(state_path)
        project_file = data_root / "projects" / state["project_id"] / "PROJECT.md"
        title = state["project_id"]
        if project_file.exists():
            first_line = project_file.read_text(encoding="utf-8").splitlines()[0]
            title = first_line.removeprefix("# ")
        rows.append(f"| `{state['project_id']}` | {title} | {state['stage']} | {state['next_action']} |")
    body = "# PaperLab 研究项目\n\n| 项目编号 | 主题 | 阶段 | 下一步 |\n|---|---|---|---|\n"
    atomic_write(data_root / "INDEX.md", body + ("\n".join(rows) if rows else "") + "\n")


def append_event(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def init_project(data_root: Path, title: str, goal: str) -> dict[str, Any]:
    data_root = data_root.resolve()
    stem = f"{date.today():%Y%m%d}_{project_slug(title)}"
    project_id = stem
    counter = 2
    while (data_root / "projects" / project_id).exists():
        project_id = f"{stem}_{counter}"
        counter += 1
    paths = project_paths(data_root, project_id)
    project_text = project_markdown(project_id, title, goal)
    if len(project_text.encode("utf-8")) > PROJECT_BUDGET:
        raise PaperLabError("project_budget_exceeded", f"PROJECT.md exceeds {PROJECT_BUDGET} bytes")
    paths["project"].mkdir(parents=True)
    (paths["project"] / "papers").mkdir()
    (paths["project"] / "evidence").mkdir()
    atomic_write(paths["project"] / "PROJECT.md", project_text)
    state = default_state(project_id)
    write_json(paths["state"], state)
    atomic_write(paths["project"] / "STATUS.md", status_markdown(state))
    if not (data_root / ".gitignore").exists():
        atomic_write(data_root / ".gitignore", private_gitignore())
    append_event(paths["events"], {"time": state["updated_at"], "action": "init", "stage": state["stage"]})
    rebuild_index(data_root)
    return {"project_id": project_id, "project_path": str(paths["project"].resolve()), "next_action": state["next_action"]}


def load_state(data_root: Path, project_id: str) -> tuple[dict[str, Any], dict[str, Path]]:
    paths = project_paths(data_root.resolve(), project_id)
    if not paths["state"].exists():
        raise PaperLabError("project_not_found", project_id)
    state = read_json(paths["state"])
    if state.get("schema_version") != 1 or state.get("project_id") != project_id:
        raise PaperLabError("invalid_state", project_id)
    return state, paths


def status_project(data_root: Path, project_id: str) -> dict[str, Any]:
    state, paths = load_state(data_root, project_id)
    backup_status = reconciled_backup_status(data_root.resolve(), project_id, state["backup_status"])
    if backup_status != state["backup_status"]:
        state["backup_status"] = backup_status
        state["updated_at"] = now_iso()
        write_json(paths["state"], state)
    status_path = paths["project"] / "STATUS.md"
    rendered = status_markdown(state)
    if not status_path.exists() or status_path.read_text(encoding="utf-8") != rendered:
        atomic_write(status_path, rendered)
    return {**state, "project_path": str(paths["project"].resolve())}


def checkpoint_project(data_root: Path, project_id: str, args: argparse.Namespace) -> dict[str, Any]:
    state, paths = load_state(data_root, project_id)
    state["stage"] = args.stage or state["stage"]
    if args.completed:
        for item in split_csv(args.completed):
            if item not in state["completed_steps"]:
                state["completed_steps"].append(item)
    if args.pending is not None:
        state["pending_actions"] = split_csv(args.pending)
    if args.next_action:
        state["next_action"] = args.next_action
    if args.selected is not None:
        state["selected_citation_keys"] = split_csv(args.selected)
    if args.processed is not None:
        state["processed_citation_keys"] = split_csv(args.processed)
    if args.bibliography_fingerprint is not None:
        state["bibliography_fingerprint"] = args.bibliography_fingerprint
    if args.backup_status is not None:
        state["backup_status"] = args.backup_status
    if args.backup:
        state["backup_status"] = "local_commit" if args.no_push else "synced"
    state["updated_at"] = now_iso()
    write_json(paths["state"], state)
    atomic_write(paths["project"] / "STATUS.md", status_markdown(state))
    append_event(
        paths["events"],
        {"time": state["updated_at"], "action": "checkpoint", "stage": state["stage"], "completed": split_csv(args.completed)},
    )
    rebuild_index(data_root.resolve())
    result = {**state, "project_path": str(paths["project"].resolve())}
    if args.backup:
        backup = backup_project(data_root.resolve(), project_id, push=not args.no_push)
        result["backup"] = backup
        if backup["status"] != state["backup_status"]:
            state["backup_status"] = backup["status"]
            state["updated_at"] = now_iso()
            write_json(paths["state"], state)
            atomic_write(paths["project"] / "STATUS.md", status_markdown(state))
            result.update(state)
    return result


def run_git(repo: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    process = subprocess.run(["git", "-C", str(repo), *arguments], capture_output=True)
    if check and process.returncode:
        message = (process.stdout + process.stderr).decode("utf-8", errors="replace").strip()
        raise PaperLabError("git_failed", message)
    return process


def reconciled_backup_status(data_root: Path, project_id: str, reported: str) -> str:
    if not (data_root / ".git").exists():
        return reported
    targets = [
        "INDEX.md",
        f"projects/{project_id}",
        f"state/{project_id}.json",
        f"events/{project_id}.jsonl",
    ]
    dirty = run_git(data_root, "status", "--porcelain", "--untracked-files=all", "--", *targets, check=False)
    if dirty.returncode == 0 and dirty.stdout:
        return "pending_push"
    if reported == "local_commit":
        return reported
    head = run_git(data_root, "rev-parse", "--verify", "HEAD", check=False)
    if head.returncode:
        return reported
    origin = run_git(data_root, "remote", "get-url", "origin", check=False)
    if origin.returncode:
        return "pending_push"
    upstream = run_git(data_root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}", check=False)
    if upstream.returncode:
        return "pending_push"
    ahead = run_git(data_root, "rev-list", "--count", "@{upstream}..HEAD", check=False)
    if ahead.returncode or int(ahead.stdout.strip() or b"0") > 0:
        return "pending_push"
    return reported


def staged_paths(data_root: Path) -> list[str]:
    output = run_git(data_root, "diff", "--cached", "--name-only", "-z").stdout
    return [item.decode("utf-8", errors="replace") for item in output.split(b"\0") if item]


def sensitive_staged_paths(data_root: Path, paths: list[str]) -> list[str]:
    problems: list[str] = []
    for relative in paths:
        normalized = relative.replace("\\", "/")
        lower = normalized.lower()
        if lower.endswith((".pdf", ".bib", ".sqlite")) or any(segment in f"/{lower}/" for segment in ("/cache/", "/assets/")):
            problems.append(relative)
            continue
        path = (data_root / relative).resolve()
        if not path.is_file():
            continue
        try:
            with path.open("r", encoding="utf-8") as handle:
                carry = ""
                while chunk := handle.read(64 * 1024):
                    normalized_text = (carry + chunk).replace("\\", "/")
                    if re.search(r"(?i)[a-z]:/[^\r\n]*/zotero/storage/", normalized_text):
                        problems.append(relative)
                        break
                    carry = normalized_text[-4096:]
        except (UnicodeDecodeError, OSError):
            continue
    return problems


def backup_project(data_root: Path, project_id: str, push: bool) -> dict[str, Any]:
    if not (data_root / ".git").exists():
        raise PaperLabError("private_git_missing", str(data_root))
    lock = data_root / ".paperlab" / "backup.lock"
    try:
        lock.mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise PaperLabError("backup_busy", "another PaperLab backup is running") from error
    try:
        targets = [
            ".gitignore",
            "INDEX.md",
            f"projects/{project_id}",
            f"state/{project_id}.json",
            f"events/{project_id}.jsonl",
        ]
        run_git(data_root, "add", "--", *targets)
        staged = staged_paths(data_root)
        sensitive = sensitive_staged_paths(data_root, staged)
        if sensitive:
            raise PaperLabError("sensitive_backup_content", ", ".join(sensitive))
        if not staged:
            return {"status": "no_changes", "commit": ""}
        state = read_json(data_root / "state" / f"{project_id}.json")
        message = f"research({project_id}): checkpoint {state['stage']}"
        run_git(
            data_root,
            "-c",
            "user.name=PaperLab",
            "-c",
            "user.email=paperlab@localhost",
            "commit",
            "-m",
            message,
        )
        commit = run_git(data_root, "rev-parse", "HEAD").stdout.decode("ascii", errors="replace").strip()
        if not push:
            return {"status": "local_commit", "commit": commit}
        remote = run_git(data_root, "remote", "get-url", "origin", check=False)
        if remote.returncode:
            return {"status": "pending_push", "commit": commit, "error": "origin remote is not configured"}
        pushed = run_git(data_root, "push", "-u", "origin", "HEAD", check=False)
        if pushed.returncode:
            error = (pushed.stdout + pushed.stderr).decode("utf-8", errors="replace").strip()
            return {"status": "pending_push", "commit": commit, "error": error}
        return {"status": "synced", "commit": commit}
    finally:
        lock.rmdir()


def doctor(data_root: Path, bibtex: Path) -> dict[str, Any]:
    try:
        import fitz  # noqa: F401

        pymupdf = True
    except Exception:
        pymupdf = False
    try:
        import pypdf  # noqa: F401

        pypdf_ready = True
    except Exception:
        pypdf_ready = False
    bibtex_entries = 0
    bibtex_ok = False
    if bibtex.exists():
        entries, errors = parse_bibtex(bibtex.read_text(encoding="utf-8"))
        bibtex_entries = len(entries)
        bibtex_ok = not errors
    checks = {
        "private_git_repo": (data_root.resolve() / ".git").exists(),
        "bibtex": bibtex_ok,
        "bibtex_entries": bibtex_entries,
        "pymupdf": pymupdf,
        "pypdf": pypdf_ready,
        "git": run_git(data_root.resolve(), "--version", check=False).returncode == 0,
    }
    return {"ready": all(checks[key] for key in ("private_git_repo", "bibtex", "pymupdf", "pypdf", "git")), "checks": checks}


def _find_matching_delimiter(text: str, start: int, opener: str, closer: str) -> int:
    depth = 0
    quote = False
    brace_depth = 0
    for index in range(start, len(text)):
        char = text[index]
        if char == '"' and (index == 0 or text[index - 1] != "\\"):
            quote = not quote
        if quote:
            continue
        if opener == "(" and char == "{":
            brace_depth += 1
            continue
        if opener == "(" and char == "}" and brace_depth:
            brace_depth -= 1
            continue
        if brace_depth:
            continue
        if char == opener:
            depth += 1
        elif char == closer:
            depth -= 1
            if depth == 0:
                return index
    return -1


def clean_bib_value(value: str) -> str:
    value = re.sub(r"\s+", " ", value.replace("\n", " ").replace("\r", " ")).strip()
    if value.startswith("{") and value.endswith("}"):
        value = value[1:-1].strip()
    return value


def parse_bibtex_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    index = 0
    while index < len(body):
        while index < len(body) and body[index] in " \r\n\t,":
            index += 1
        match = re.match(r"([A-Za-z][A-Za-z0-9_-]*)\s*=", body[index:])
        if not match:
            break
        name = match.group(1).lower()
        index += match.end()
        while index < len(body) and body[index].isspace():
            index += 1
        if index >= len(body):
            break
        if body[index] == "{":
            end = _find_matching_delimiter(body, index, "{", "}")
            value = body[index + 1 : end if end >= 0 else len(body)].strip()
            index = end + 1 if end >= 0 else len(body)
        elif body[index] == '"':
            index += 1
            start = index
            while index < len(body) and not (body[index] == '"' and body[index - 1] != "\\"):
                index += 1
            value = body[start:index].strip()
            index += 1
        else:
            start = index
            while index < len(body) and body[index] != ",":
                index += 1
            value = body[start:index].strip()
        fields[name] = clean_bib_value(value)
        while index < len(body) and body[index] != ",":
            index += 1
        index += index < len(body)
    return fields


def parse_bibtex(text: str) -> tuple[list[dict[str, Any]], list[str]]:
    entries: list[dict[str, Any]] = []
    errors: list[str] = []
    position = 0
    while True:
        at = text.find("@", position)
        if at < 0:
            break
        match = re.match(r"@([A-Za-z]+)\s*([\{(])\s*([^,\s]+)\s*,", text[at:])
        if not match:
            errors.append(f"cannot parse entry near offset {at}")
            position = at + 1
            continue
        entry_type, opener, key = match.group(1), match.group(2), match.group(3)
        body_start = at + match.start(2)
        body_end = _find_matching_delimiter(text, body_start, opener, "}" if opener == "{" else ")")
        if body_end < 0:
            errors.append(f"cannot find entry body: {key}")
            position = at + 1
            continue
        fields = parse_bibtex_fields(text[at + match.end() : body_end].strip().rstrip(","))
        title = fields.get("title", "")
        file_value = fields.get("file", "")
        file_paths = []
        for raw in file_value.split(";") if file_value else []:
            candidate = raw.strip().replace(r"\:", ":").replace(r"\\", "\\")
            pdf_match = re.match(r"(?P<path>.*?\.pdf)(?::[^:]*)?$", candidate, flags=re.I)
            file_paths.append((pdf_match.group("path") if pdf_match else candidate).strip())
        authors = [part.strip() for part in re.split(r"\s+and\s+", fields.get("author", "")) if part.strip()]
        entries.append(
            {
                "citation_key": key,
                "entry_type": entry_type.lower(),
                "title": title,
                "authors": authors,
                "year": fields.get("year") or fields.get("date", "")[:4],
                "publication": fields.get("journaltitle") or fields.get("journal") or fields.get("booktitle") or fields.get("publisher", ""),
                "volume": fields.get("volume", ""),
                "issue": fields.get("number") or fields.get("issue", ""),
                "pages": fields.get("pages", ""),
                "doi": normalize_doi(fields.get("doi")),
                "url": fields.get("url", ""),
                "abstract": fields.get("abstract", ""),
                "keywords": split_csv(fields.get("keywords", "").replace(";", ",")),
                "file": file_paths,
                "normalized_title": normalize_title(title),
                "raw_fields": fields,
            }
        )
        position = body_end + 1
    return entries, errors


def existing_pdfs(record: dict[str, Any]) -> list[str]:
    return [path for path in record.get("file") or [] if path.lower().endswith(".pdf") and Path(path).is_file()]


def match_candidates(entries: list[dict[str, Any]], candidates_path: Path) -> dict[str, Any]:
    if not candidates_path.exists():
        raise PaperLabError("candidates_not_found", str(candidates_path))
    candidates = read_json(candidates_path)
    matches: list[dict[str, Any]] = []
    ready = missing_pdf = not_in_zotero = 0
    for candidate in candidates:
        doi = normalize_doi(candidate.get("doi"))
        title = normalize_title(candidate.get("title"))
        doi_records = [record for record in entries if doi and record["doi"] == doi]
        title_records = [record for record in entries if title and record["normalized_title"] == title]
        if doi_records:
            records = doi_records + [
                record
                for record in title_records
                if record not in doi_records and (not record["doi"] or record["doi"] == doi)
            ]
            matched_by = "doi"
        else:
            records = title_records
            matched_by = "title" if records else ""
        if not records:
            not_in_zotero += 1
            matches.append(
                {
                    "candidate_id": candidate.get("id"),
                    "status": "not_in_zotero",
                    "matched_by": "",
                    "citation_key": "",
                    "pdf_count": 0,
                    "duplicate_keys": [],
                }
            )
            continue
        ranked = sorted(records, key=lambda record: len(existing_pdfs(record)), reverse=True)
        preferred = ranked[0]
        pdf_count = len(existing_pdfs(preferred))
        status = "ready" if pdf_count else "missing_pdf"
        ready += status == "ready"
        missing_pdf += status == "missing_pdf"
        matches.append(
            {
                "candidate_id": candidate.get("id"),
                "status": status,
                "matched_by": matched_by,
                "citation_key": preferred["citation_key"],
                "pdf_count": pdf_count,
                "duplicate_keys": [record["citation_key"] for record in records] if len(records) > 1 else [],
            }
        )
    return {
        "readiness": {
            "candidate_count": len(candidates),
            "matched": ready + missing_pdf,
            "ready": ready,
            "missing_pdf": missing_pdf,
            "not_in_zotero": not_in_zotero,
        },
        "matches": matches,
    }


def sync_library(bibtex: Path, index: Path, candidates: Path | None = None) -> dict[str, Any]:
    bibtex = bibtex.resolve()
    index = index.resolve()
    if not bibtex.exists():
        raise PaperLabError("bibtex_not_found", str(bibtex))
    entries, errors = parse_bibtex(bibtex.read_text(encoding="utf-8"))
    if errors:
        raise PaperLabError("bibtex_parse_error", "; ".join(errors))
    write_json(index, entries)
    result = {"entry_count": len(entries), "fingerprint": file_sha256(bibtex), "index": str(index)}
    if candidates:
        result.update(match_candidates(entries, candidates.resolve()))
    return result


def extract_pdf(pdf: Path, cache_dir: Path) -> dict[str, Any]:
    pdf = pdf.resolve()
    if not pdf.exists():
        return {"status": "missing", "pages": [], "source_sha256": ""}
    digest = file_sha256(pdf)
    cache_path = cache_dir.resolve() / f"{digest}.json"
    if cache_path.exists():
        cached = read_json(cache_path)
        if cached.get("source_sha256") == digest:
            return cached
    try:
        import fitz

        document = fitz.open(pdf)
        if document.needs_pass or document.is_encrypted:
            document.close()
            return {"status": "encrypted", "pages": [], "source_sha256": digest}
        pages = [{"page": index + 1, "text": document.load_page(index).get_text("text") or ""} for index in range(document.page_count)]
        document.close()
    except Exception as fitz_error:
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(pdf))
            if reader.is_encrypted:
                return {"status": "encrypted", "pages": [], "source_sha256": digest}
            pages = [{"page": index + 1, "text": page.extract_text() or ""} for index, page in enumerate(reader.pages)]
        except Exception as pypdf_error:
            return {"status": "corrupt", "pages": [], "source_sha256": digest, "error": f"{fitz_error}; {pypdf_error}"}
    if pages and sum(len(page["text"]) for page in pages[:3]) < 80:
        return {"status": "scanned_suspect", "pages": [], "source_sha256": digest, "page_count": len(pages)}
    result = {"status": "ok", "pages": pages, "source_sha256": digest, "page_count": len(pages)}
    write_json(cache_path, result)
    return result


def parse_page_spec(value: str | None, page_count: int) -> list[int]:
    if not value:
        return list(range(page_count))
    selected: list[int] = []
    for raw_part in value.split(","):
        part = raw_part.strip()
        range_match = re.fullmatch(r"(\d+)\s*-\s*(\d+)", part)
        page_match = re.fullmatch(r"\d+", part)
        if range_match:
            start, end = (int(item) for item in range_match.groups())
            if start < 1 or end < start or end > page_count:
                raise PaperLabError("invalid_page_spec", value)
            selected.extend(range(start - 1, end))
        elif page_match:
            page = int(part)
            if not 1 <= page <= page_count:
                raise PaperLabError("invalid_page_spec", value)
            selected.append(page - 1)
        else:
            raise PaperLabError("invalid_page_spec", value)
    return selected


def read_pages(pdf: Path, cache_dir: Path, page_spec: str | None) -> dict[str, Any]:
    extracted = extract_pdf(pdf, cache_dir)
    if extracted["status"] != "ok":
        return extracted
    all_pages = extracted["pages"]
    indexes = parse_page_spec(page_spec, len(all_pages))
    output = [all_pages[index] for index in indexes]
    return {
        "status": "ok",
        "pages": output,
        "source_sha256": extracted["source_sha256"],
        "page_count": extracted["page_count"],
        "truncated": False,
        "character_count": sum(len(page["text"]) for page in output),
    }


SECTION_HEADING = re.compile(r"^\s*(?:\d+(?:\.\d+)*[.)]?\s+)([^\n]{2,100})\s*$")
SECTION_NUMBER = re.compile(r"^\d+(?:\.\d+)*[.)]?$")
REFERENCE_HEADING = re.compile(r"^\s*(?:\d+(?:\.\d+)*[.)]?\s+)?(?:references|bibliography)\s*$", re.I)


def _title_like(value: str) -> bool:
    return bool(value and len(value) <= 80 and (value[0].isupper() or "\u4e00" <= value[0] <= "\u9fff"))


def _reference_boundary(pages: list[dict[str, Any]]) -> tuple[int | None, int | None]:
    for page in pages:
        lines = [line.strip() for line in page["text"].splitlines() if line.strip()]
        for line_index, line in enumerate(lines):
            if REFERENCE_HEADING.fullmatch(line):
                page_number = page["page"]
                return page_number, page_number - 1 if line_index == 0 else page_number
    return None, None


def _heuristic_outline(pages: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int | None]:
    headings: list[tuple[str, int]] = []
    references_start, content_end_page = _reference_boundary(pages)
    for page in pages:
        lines = [line.strip() for line in page["text"].splitlines() if line.strip()]
        for line_index, line in enumerate(lines):
            if REFERENCE_HEADING.fullmatch(line):
                break
            match = SECTION_HEADING.fullmatch(line)
            title = match.group(1).strip() if match else ""
            if not title and SECTION_NUMBER.fullmatch(line) and line_index + 1 < len(lines):
                title = lines[line_index + 1]
            if _title_like(title):
                headings.append((title, page["page"]))
                break
        if references_start == page["page"]:
            break
    sections: list[dict[str, Any]] = []
    for index, (title, start_page) in enumerate(headings):
        next_start = headings[index + 1][1] if index + 1 < len(headings) else (content_end_page or len(pages)) + 1
        sections.append({"title": title, "start_page": start_page, "end_page": next_start - 1, "source": "heuristic"})
    return sections, references_start


def read_outline(pdf: Path, cache_dir: Path) -> dict[str, Any]:
    extracted = extract_pdf(pdf, cache_dir)
    if extracted["status"] != "ok":
        return extracted
    sections: list[dict[str, Any]] = []
    fallback_references, fallback_content_end = _reference_boundary(extracted["pages"])
    try:
        import fitz

        with fitz.open(pdf.resolve()) as document:
            raw_toc = [(level, title.strip(), page) for level, title, page, *_ in document.get_toc() if page > 0]
    except Exception:
        raw_toc = []
    toc_references = next((page for _, title, page in raw_toc if REFERENCE_HEADING.fullmatch(title)), None)
    references_start = toc_references or fallback_references
    content_end_page = (
        fallback_content_end
        if toc_references and fallback_references == toc_references and fallback_content_end is not None
        else (toc_references - 1 if toc_references else fallback_content_end)
    )
    toc = [(title, page) for level, title, page in raw_toc if level == 1 and not REFERENCE_HEADING.fullmatch(title)]
    if toc:
        for index, (title, start_page) in enumerate(toc):
            next_start = toc[index + 1][1] if index + 1 < len(toc) else extracted["page_count"] + 1
            end_page = max(start_page, next_start - 1)
            if references_start and start_page <= references_start < next_start and content_end_page is not None:
                end_page = max(start_page, min(end_page, content_end_page))
            sections.append({"title": title, "start_page": start_page, "end_page": end_page, "source": "toc"})
    else:
        sections, references_start = _heuristic_outline(extracted["pages"])
    return {
        "status": "ok",
        "page_count": extracted["page_count"],
        "sections": sections,
        "references_start": references_start,
        "source_sha256": extracted["source_sha256"],
    }


def parse_clip(value: str | None) -> list[float]:
    if not value:
        return [0.0, 0.0, 1.0, 1.0]
    try:
        clip = [float(item.strip()) for item in value.split(",")]
    except ValueError as error:
        raise PaperLabError("invalid_clip", value) from error
    if len(clip) != 4 or not (0 <= clip[0] < clip[2] <= 1 and 0 <= clip[1] < clip[3] <= 1):
        raise PaperLabError("invalid_clip", value)
    return clip


def _normalized_box(rect: Any, page_rect: Any, padding: float = 0.0) -> list[float]:
    return [
        max(0.0, round((rect.x0 - page_rect.x0) / page_rect.width - padding, 4)),
        max(0.0, round((rect.y0 - page_rect.y0) / page_rect.height - padding, 4)),
        min(1.0, round((rect.x1 - page_rect.x0) / page_rect.width + padding, 4)),
        min(1.0, round((rect.y1 - page_rect.y0) / page_rect.height + padding, 4)),
    ]


def inspect_page(pdf: Path, page_number: int, label: str) -> dict[str, Any]:
    pdf = pdf.resolve()
    if not pdf.exists():
        raise PaperLabError("pdf_not_found", str(pdf))
    try:
        import fitz

        with fitz.open(pdf) as document:
            if document.needs_pass or document.is_encrypted:
                raise PaperLabError("encrypted_pdf", str(pdf))
            if not 1 <= page_number <= document.page_count:
                raise PaperLabError("invalid_page", str(page_number))
            page = document.load_page(page_number - 1)
            page_rect = page.rect
            text_blocks = [block for block in page.get_text("blocks") if len(block) > 6 and block[6] == 0]
            object_rects = [fitz.Rect(drawing["rect"]) for drawing in page.get_drawings()]
            object_rects.extend(
                fitz.Rect(block["bbox"])
                for block in page.get_text("dict").get("blocks", [])
                if block.get("type") == 1
            )
            object_rects = [rect for rect in object_rects if not rect.is_infinite and rect.width + rect.height > 4]
            object_rects = [
                fitz.Rect(
                    rect.x0 - (1 if rect.width == 0 else 0),
                    rect.y0 - (1 if rect.height == 0 else 0),
                    rect.x1 + (1 if rect.width == 0 else 0),
                    rect.y1 + (1 if rect.height == 0 else 0),
                )
                for rect in object_rects
            ]

            needle = normalize_title(label)
            matches: list[dict[str, Any]] = []
            for block in text_blocks:
                text = re.sub(r"\s+", " ", block[4]).strip()
                normalized_text = normalize_title(text)
                if normalized_text != needle and not normalized_text.startswith(needle + " "):
                    continue
                caption = fitz.Rect(block[:4])
                horizontal_margin = page_rect.width * 0.1

                def nearby(rect: Any, direction: str) -> bool:
                    overlaps_column = rect.x1 >= caption.x0 - horizontal_margin and rect.x0 <= caption.x1 + horizontal_margin
                    if not overlaps_column:
                        return False
                    if direction == "above":
                        return rect.y1 <= caption.y0 + page_rect.height * 0.03 and caption.y0 - rect.y1 <= page_rect.height * 0.45
                    return rect.y0 >= caption.y1 - page_rect.height * 0.03 and rect.y0 - caption.y1 <= page_rect.height * 0.45

                above = [rect for rect in object_rects if nearby(rect, "above")]
                below = [rect for rect in object_rects if nearby(rect, "below")]
                score = lambda rects: sum(max(rect.width, 2) * max(rect.height, 2) for rect in rects)
                above_score, below_score = score(above), score(below)
                if above_score or below_score:
                    direction = "above" if above_score >= below_score else "below"
                    selected = above if direction == "above" else below
                    region = fitz.Rect(caption)
                    for rect in selected:
                        region.include_rect(rect)
                    confidence = "high"
                else:
                    direction = "above" if normalize_title(label).startswith(("fig ", "figure ")) else "below"
                    if direction == "above":
                        region = fitz.Rect(page_rect.x0 + page_rect.width * 0.05, max(page_rect.y0, caption.y0 - page_rect.height * 0.3), page_rect.x1 - page_rect.width * 0.05, caption.y1)
                    else:
                        region = fitz.Rect(page_rect.x0 + page_rect.width * 0.05, caption.y0, page_rect.x1 - page_rect.width * 0.05, min(page_rect.y1, caption.y1 + page_rect.height * 0.3))
                    selected = []
                    confidence = "low"
                matches.append(
                    {
                        "caption": text[:160],
                        "caption_bbox": _normalized_box(caption, page_rect),
                        "suggested_clip": _normalized_box(region, page_rect, padding=0.02),
                        "direction": direction,
                        "confidence": confidence,
                        "object_count": len(selected),
                    }
                )
    except PaperLabError:
        raise
    except Exception as error:
        raise PaperLabError("inspect_failed", str(error)) from error
    return {
        "status": "ok" if matches else "not_found",
        "page": page_number,
        "label": label,
        "matches": matches,
        "source_sha256": file_sha256(pdf),
    }


def render_page(pdf: Path, page_number: int, output: Path, clip_value: str | None) -> dict[str, Any]:
    pdf = pdf.resolve()
    output = output.resolve()
    if not pdf.exists():
        raise PaperLabError("pdf_not_found", str(pdf))
    if output.suffix.lower() != ".png":
        raise PaperLabError("invalid_output", "render output must be PNG")
    clip = parse_clip(clip_value)
    try:
        import fitz

        with fitz.open(pdf) as document:
            if document.needs_pass or document.is_encrypted:
                raise PaperLabError("encrypted_pdf", str(pdf))
            if not 1 <= page_number <= document.page_count:
                raise PaperLabError("invalid_page", str(page_number))
            page = document.load_page(page_number - 1)
            rect = page.rect
            region = fitz.Rect(
                rect.x0 + rect.width * clip[0],
                rect.y0 + rect.height * clip[1],
                rect.x0 + rect.width * clip[2],
                rect.y0 + rect.height * clip[3],
            )
            content = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5), clip=region, alpha=False).tobytes("png")
    except PaperLabError:
        raise
    except Exception as error:
        raise PaperLabError("render_failed", str(error)) from error
    try:
        atomic_write_bytes(output, content)
        status = "created"
    except FileExistsError:
        if output.read_bytes() == content:
            status = "cached"
        else:
            raise PaperLabError("output_exists", str(output))
    return {
        "status": status,
        "output": str(output),
        "page": page_number,
        "clip": clip,
        "source_sha256": file_sha256(pdf),
        "width": round(region.width * 2.5),
        "height": round(region.height * 2.5),
    }


def ris_type(record: dict[str, Any]) -> str:
    kind = str(record.get("type") or record.get("entry_type") or "").lower()
    if "conference" in kind or "inproceedings" in kind:
        return "CPAPER"
    if "book" in kind:
        return "BOOK"
    if "thesis" in kind:
        return "THES"
    return "JOUR"


def generate_ris(input_path: Path, ids: list[str], output: Path) -> dict[str, Any]:
    records = read_json(input_path.resolve())
    by_id = {str(record.get("id")): record for record in records}
    selected = [by_id[item] for item in ids if item in by_id]
    rejected: list[Any] = []
    duplicates: list[Any] = []
    exported: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record in selected:
        record_id = record.get("id")
        if record.get("verification") != "verified":
            rejected.append(record_id)
            continue
        doi = normalize_doi(record.get("doi"))
        identity = f"doi:{doi}" if doi else f"title:{normalize_title(record.get('title'))}"
        if not identity.split(":", 1)[1] or identity in seen:
            duplicates.append(record_id)
            continue
        seen.add(identity)
        exported.append({**record, "doi": doi})
    lines: list[str] = []
    for record in exported:
        lines.append(f"TY  - {ris_type(record)}")
        lines.append(f"TI  - {record.get('title', '')}")
        for author in record.get("authors") or []:
            lines.append(f"AU  - {author}")
        for tag, key in (("PY", "year"), ("JO", "publication"), ("DO", "doi"), ("UR", "url"), ("AB", "abstract")):
            if record.get(key):
                lines.append(f"{tag}  - {record[key]}")
        for keyword in record.get("keywords") or []:
            lines.append(f"KW  - {keyword}")
        lines.extend(["ER  - ", ""])
    output = output.resolve()
    atomic_write(output, "\n".join(lines))
    return {"exported": len(exported), "rejected": rejected, "duplicates": duplicates, "output": str(output)}


def emit(payload: dict[str, Any]) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PaperLab internal workflow engine", allow_abbrev=False)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init")
    init.add_argument("--data-root", type=Path, required=True)
    init.add_argument("--title", required=True)
    init.add_argument("--goal", required=True)

    status = subparsers.add_parser("status")
    status.add_argument("--data-root", type=Path, required=True)
    status.add_argument("--project", required=True)

    checkpoint = subparsers.add_parser("checkpoint")
    checkpoint.add_argument("--data-root", type=Path, required=True)
    checkpoint.add_argument("--project", required=True)
    checkpoint.add_argument("--stage")
    checkpoint.add_argument("--completed")
    checkpoint.add_argument("--pending")
    checkpoint.add_argument("--next", dest="next_action")
    checkpoint.add_argument("--selected")
    checkpoint.add_argument("--processed")
    checkpoint.add_argument("--bibliography-fingerprint")
    checkpoint.add_argument("--backup-status")
    checkpoint.add_argument("--backup", action="store_true")
    checkpoint.add_argument("--no-push", action="store_true")

    sync = subparsers.add_parser("sync")
    sync.add_argument("--bibtex", type=Path, required=True)
    sync.add_argument("--index", type=Path, required=True)
    sync.add_argument("--candidates", type=Path)

    read = subparsers.add_parser("read")
    read.add_argument("--pdf", type=Path, required=True)
    read.add_argument("--cache-dir", type=Path, required=True)
    read.add_argument("--pages")
    read.add_argument("--outline", action="store_true")

    render = subparsers.add_parser("render")
    render.add_argument("--pdf", type=Path, required=True)
    render.add_argument("--page", type=int, required=True)
    render.add_argument("--clip")
    render.add_argument("--output", type=Path, required=True)

    inspect = subparsers.add_parser("inspect")
    inspect.add_argument("--pdf", type=Path, required=True)
    inspect.add_argument("--page", type=int, required=True)
    inspect.add_argument("--label", required=True)

    ris = subparsers.add_parser("ris")
    ris.add_argument("--input", type=Path, required=True)
    ris.add_argument("--ids", required=True)
    ris.add_argument("--output", type=Path, required=True)

    doctor_parser = subparsers.add_parser("doctor")
    doctor_parser.add_argument("--data-root", type=Path, required=True)
    doctor_parser.add_argument("--bibtex", type=Path, required=True)
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "init":
        return init_project(args.data_root, args.title, args.goal)
    if args.command == "status":
        return status_project(args.data_root, args.project)
    if args.command == "checkpoint":
        return checkpoint_project(args.data_root, args.project, args)
    if args.command == "sync":
        return sync_library(args.bibtex, args.index, args.candidates)
    if args.command == "read":
        return read_outline(args.pdf, args.cache_dir) if args.outline else read_pages(args.pdf, args.cache_dir, args.pages)
    if args.command == "render":
        return render_page(args.pdf, args.page, args.output, args.clip)
    if args.command == "inspect":
        return inspect_page(args.pdf, args.page, args.label)
    if args.command == "ris":
        return generate_ris(args.input, split_csv(args.ids), args.output)
    if args.command == "doctor":
        return doctor(args.data_root, args.bibtex)
    raise PaperLabError("unknown_command", args.command)


def main() -> int:
    try:
        emit(run(build_parser().parse_args()))
        return 0
    except PaperLabError as error:
        emit({"error": error.code, "message": str(error)})
        return 2
    except Exception as error:
        emit({"error": "internal_error", "message": str(error)})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
