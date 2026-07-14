---
name: paper-research
description: Manage long-running Zotero literature research through natural-language requests. Use for starting, continuing, restoring, searching, importing, screening, reading, comparing, or synthesizing papers and research topics in this repository, including Chinese requests such as 开始研究、继续、恢复项目、找论文、导入 Zotero、精读论文、比较文献、争议分析、研究缺口.
---

# Paper Research

Treat one Codex task as one research project. Keep durable state in files; never rely on chat history as the only record.

## Resolve the project

Use `<repo>/research` as the private data repository and `<repo>/.paperlab/paperlab.py` as the deterministic engine.

- For “开始研究 X”, clarify at most one material ambiguity, then run `init` and bind this task to the returned `project_id`.
- For “继续”, reuse the bound project, read `PROJECT.md` and `STATUS.md`, run `status`, and execute `next_action`.
- For “恢复项目 X”, match X against `research/INDEX.md`; ask when multiple projects match.
- If binding is missing, list project titles. Never guess from modification time and never maintain a global active project.
- Retry `checkpoint --backup` first when `backup_status` is `pending_push`; continue locally if push still fails.
- After `init`, set the task title to `研究｜<简短主题>` when task-title control is available.
- End every research response with exactly: `当前项目：<project_id>；下一步：<action>`.

## Context and evidence

- Keep `PROJECT.md` under 4 KB and `STATUS.md` under 2 KB.
- Show at most 每轮最多 15 篇 search candidates unless another batch is requested.
- Use `read --outline` first, then read every relevant section completely. PDF reading does 不设置固定页数或字符上限.
- 检测到 References 后停止. Read references, acknowledgements, or biographies only to verify a citation; read relevant appendices when the research question requires them.
- 多篇比较每批最多 5 张证据卡. Keep each card near 2,000 Chinese characters.
- 不得读取完整 `library.bib`, cache directory, or all detailed notes into context. Use `sync`, outlines, evidence cards, and exact source pages.
- Reopen source pages to verify values, figures, tables, equations, or disputed claims.

## Discover

1. Read the current `PROJECT.md`.
2. Prefer the installed academic-search workflow; otherwise use web search and primary scholarly sources.
3. Verify title, authors, year, DOI or stable URL. Never invent missing metadata.
4. Deduplicate by normalized DOI, then normalized title.
5. Save numbered candidates to `search.md` and structured candidates to `candidates.json`.
6. Mark unverified records and exclude them from RIS export.
7. Run `sync --candidates` and report exactly one readiness line: `候选：<n>｜已在 Zotero：<n>｜有 PDF：<n>｜可精读：<n>｜待导入：<n>`.
8. Explain what the selected roles can support: field map, method evidence, comparison, or background.
9. Checkpoint after saving results.

## Import to Zotero

1. Accept selections such as “第 2、5、7 篇”.
2. Run `ris` only for selected, verified records and verify the exported count and titles.
3. Save `zotero_import.ris` in the project directory.
4. On Windows, open 资源管理器 and select the RIS file. Give its absolute path, record count, and titles in the same response.
5. Explain once that RIS contains metadata, not PDFs, and ask only for Zotero import plus legal PDF attachment.
6. Never write directly to Zotero, `zotero.sqlite`, or Zotero `storage`.

## Sync and screen

1. Run `sync --candidates` against the current `bibliography/library.bib`; never trust a stale index.
2. Match by DOI first, exact normalized title second. Prefer a duplicate record with an existing PDF while reporting every duplicate citation key.
3. Show the readiness line before asking what to read.
4. Screen from metadata or abstract only when full text is unavailable and label that evidence basis.
5. Save decisions and unresolved checks in `screening.md`. Never treat an abstract as full-text evidence.

## Read, translate, learn, and export

Read [references/deep-reading.md](references/deep-reading.md) before any full-text reading or multi-paper batch. It is the fixed reading method and artifact contract.

1. Resolve the PDF from the local index; never edit, rename, copy, or delete the source PDF. Record its SHA-256 before reading.
2. Run `read --outline`, then read each relevant natural section once. If a section is too large for the platform, divide it by its own subsections or page boundary without introducing a fixed numeric cap or omitting pages.
3. Stop normal reading at the detected reference boundary. Read relevant appendices; use references only for citation verification.
4. Produce two distinct manuscripts from the same extraction cache:
   - `translations/<citation_key>.md`: 中文全文对照版，按原论文的章节与页码对齐，不得压缩成摘要。
   - `papers/<citation_key>.md`: 精读学习版，沿作者的论证顺序逐节解释，不得用“问题、方法、结果、贡献”重新横向切块。
5. Record page, section, figure, table, or equation references beside the claim they support. Keep the separate evidence card for later comparison.
6. Report encrypted, corrupt, or scanned PDFs. Do not run OCR without explicit approval.
7. For each used figure or table, call `inspect --page <n> --label <label>` first. Render and visually inspect only the final crop; use one low-detail full-page fallback only when matching is uncertain or incomplete.
8. Save local PNGs under `projects/<id>/assets/<citation_key>/`; place each used image beside the paragraph that teaches it. Reuse assets whose source hash still matches.
9. Keep hidden `PAPERLAB:FIGURES` JSON in the AUTO block. When refreshing, replace only `PAPERLAB:AUTO`; preserve `## 人工确认` and all user text byte-for-byte.
10. Export both manuscripts with the engine `export` command to `output/pdf/<project_id>/`. Use `<short_title>_中文全文对照.pdf` and `<short_title>_精读学习.pdf`; do not replace an existing PDF unless the revised manuscript has been validated and `--replace` is explicit. The engine's automatic PDF validation must pass before replacement or checkpoint; on failure, preserve the existing PDF and report the validation error.
11. The Chinese companion must say `机器辅助翻译，原文为准`. The learning PDF must contain a progressive reading route, section transitions, the complete argument chain, limitations, and next reading.
12. In the completion response, display only the most useful one or two figures and provide absolute links to both PDFs.

Keep this update boundary in both manuscripts:

```markdown
<!-- PAPERLAB:AUTO:START -->

Automatically generated translation or learning narrative.

<!-- PAPERLAB:AUTO:END -->

## 人工确认

User-maintained content. Codex不得覆盖 this section.
```

## Parallel deep reading

For two or more requested papers, use 每篇论文一个子代理 when subagents are available.

1. The 协调代理 resolves citation keys, source paths, hashes, project questions, and unique output paths before delegation.
2. Give each subagent exactly one paper and the fixed method in `references/deep-reading.md`. The subagent may write only its own translation, learning note, evidence card, and asset directory.
3. 只有协调代理可以更新 `PROJECT.md`, `STATUS.md`, `state/<project_id>.json`, events, `synthesis.md`, or Git. Subagents never checkpoint, commit, push, or edit another paper.
4. Start as many papers as the user requested up to available slots. When slots are fewer than papers, 分波次 without reducing the requested set.
5. 一个论文失败不得取消其他论文. Preserve successful artifacts and retry only failed or incomplete papers.
6. As results arrive, the coordinator validates source coverage, page anchors, images, human-section preservation, and source PDF hash. Then it updates state sequentially.
7. Perform one private backup after the validated batch. Report completed, failed, pending-retry, and next-wave counts.
8. If subagents are unavailable, run the identical per-paper contract sequentially rather than silently weakening the outputs.

## Synthesize

1. Compare the processed evidence against every core question in `PROJECT.md` before writing.
2. If coverage is incomplete, still answer the user but label it 阶段性综合 and state the missing evidence. Never imply a complete field history from a partial reading set.
3. Read evidence cards in batches of at most five and reopen only disputed source pages.
4. Compare definitions, methods, samples, settings, results, limitations, and evidence strength.
5. Separate genuine contradictions from differences in definitions, samples, metrics, or conditions.
6. Do not equate “few papers found” with “nobody has studied this”.
7. Write comparisons, disputes, evidence assessment, gaps, and executable questions to `synthesis.md`.

## Checkpoint and backup

After each search selection, screening batch, completed paper note, or synthesis update:

1. Finish the artifact first.
2. Run `checkpoint --backup`; `--completed` must 只传本次新增 step because the engine retains prior history.
3. Validate a whole batch once instead of repeating the same structural audit after every small operation.
4. If push fails, retain the local commit, report `pending_push`, and continue research.
5. Never stage PDFs, BibTeX, full-text caches, local figure assets, Zotero storage paths, secrets, cookies, or databases.

## Failure handling

- Missing BibTeX: give the single Better BibTeX export action needed.
- Missing PDF: provide legal publisher, DOI, open-access, or repository routes; do not bypass access controls.
- Missing local figure asset: regenerate it from the hidden render recipe only when the source PDF hash matches.
- Existing output: preserve the human section and replace only AUTO content.
- Tool failure: record it in pending actions, save a checkpoint, and continue independent work.
- Long task or compaction: reconstruct from project files and artifacts, not remembered conversation details.
