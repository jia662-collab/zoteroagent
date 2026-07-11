---
name: paper-research
description: Manage long-running Zotero literature research through natural-language requests. Use for starting, continuing, restoring, searching, importing, screening, reading, comparing, or synthesizing papers and research topics in this repository, including Chinese requests such as 开始研究、继续、恢复项目、找论文、导入 Zotero、精读论文、比较文献、争议分析、研究缺口.
---

# Paper Research

Treat one Codex task as one research project. Keep durable state in files; never rely on chat history as the only record.

## Resolve the project

Use `<repo>/research` as the private data repository and `<repo>/.paperlab/paperlab.py` as the deterministic engine.

- For “开始研究 X”, clarify at most one material ambiguity, then run `init` and bind this task to the returned `project_id`.
- For “继续”, reuse the bound `project_id`, read its `PROJECT.md` and `STATUS.md`, run `status`, and execute `next_action`.
- For “恢复项目 X”, match X against `research/INDEX.md`; ask the user when more than one project matches.
- If binding is missing, list project titles. Never guess from modification time.
- After `status`, retry `checkpoint --backup` first when `backup_status` is `pending_push`; continue locally if the retry still cannot push.
- After `init`, set the Codex task title to `研究｜<简短主题>` when task-title control is available.
- Never maintain a global active project.
- End every research response with exactly one short line in this form: `当前项目：<project_id>；下一步：<action>`.

## Context budget

- Keep `PROJECT.md` under 4 KB and `STATUS.md` under 2 KB.
- Show and save 每轮最多 15 篇 search candidates unless the user requests another batch.
- Read a PDF in chunks of 最多 8 页 and 20,000 characters through `read`.
- For comparison, load 最多 5 张证据卡 at a time.
- Keep each evidence card near 2,000 Chinese characters or less.
- Do not load all detailed notes, logs, caches, or papers at once.
- 不得读取完整 `library.bib` into model context. Run `sync` and query the generated local index instead.
- Reopen source pages only to verify exact values, figures, tables, equations, or disputed claims.

## Workflow

### Discover

1. Read the current `PROJECT.md`.
2. Prefer the installed `nature-academic-search` workflow; otherwise use web search and primary scholarly sources.
3. Verify title, authors, year, DOI or stable URL. Do not invent missing metadata.
4. Deduplicate by normalized DOI, then normalized title.
5. Write numbered candidates to `search.md` and structured candidates to `candidates.json`.
6. Mark unverified records explicitly and exclude them from RIS export.
7. Checkpoint after saving results.

### Import to Zotero

1. Accept selections such as “第 2、5、7 篇”.
2. Run `ris` for selected verified candidate IDs.
3. Save `zotero_import.ris` in the project directory.
4. Ask the user only to import that file into Zotero.
5. Never write directly to Zotero, `zotero.sqlite`, or Zotero `storage`.

### Sync and screen

1. Run `sync` against `bibliography/library.bib`; it always parses the current BibTeX source.
2. Match imported papers by DOI first, then verified title.
3. Screen from metadata or abstract only when full text is unavailable and label the evidence basis.
4. Save decisions and unresolved checks in `screening.md`.
5. Do not treat an abstract as full-text evidence.

### Read

1. Resolve the PDF path from the local index and call `read`; never edit, rename, copy, or delete the source PDF.
2. Read sequential page chunks, saving progress after each chunk.
3. Record page, section, figure, or table references for important claims.
4. Report encrypted, corrupt, or scanned PDFs. Do not run OCR without explicit user approval.
5. Write a detailed paper note and a compact evidence card.

Use these exact boundaries in every detailed note:

```markdown
# Paper title

<!-- PAPERLAB:AUTO:START -->
## 自动分析

Generated, source-grounded analysis.
<!-- PAPERLAB:AUTO:END -->

## 人工确认

User-maintained content. Codex不得覆盖 this section.
```

When refreshing a note, replace only the text between the AUTO markers. Preserve everything else byte-for-byte.

Classify claims as:

- 作者明确陈述
- 数据直接支持
- 合理推断
- Codex 的解释
- 无法确认

### Synthesize

1. Read evidence cards in batches of at most five.
2. Compare definitions, methods, samples, conditions, results, limitations, and evidence strength.
3. Separate genuine contradictions from differences in definitions, samples, metrics, or settings.
4. Do not equate “few papers found” with “nobody has studied this”.
5. Write comparison, disputes, evidence assessment, knowledge gaps, and executable research questions to `synthesis.md`.

## Checkpoint and backup

After each search selection, screening batch, completed paper note, or synthesis update:

1. Finish the artifact first.
2. Run `checkpoint --backup` with the completed step and next action.
3. If push is unavailable, keep the local commit and report `pending_push`; continue research instead of failing the task.
4. Never stage PDFs, BibTeX, full-text caches, Zotero absolute storage paths, secrets, cookies, or databases.

## Failure handling

- Missing BibTeX: give the single Better BibTeX export action needed.
- Missing PDF: provide legal publisher, DOI, open-access, or repository routes; do not bypass access controls.
- Existing output: preserve human sections and merge only the automatic section.
- Tool failure: record it in pending actions, save a checkpoint, and continue independent work.
- Long task or compaction: reconstruct from `PROJECT.md`, state JSON, `STATUS.md`, and artifacts, not from remembered conversation details.
