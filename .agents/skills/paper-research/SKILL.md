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

## Read and illustrate

1. Resolve the PDF from the local index; never edit, rename, copy, or delete the source PDF.
2. Run `read --outline`, then read each relevant natural section once. If a section is too large for the platform, divide it by its own subsections or page boundary without introducing a fixed numeric cap or omitting pages.
3. Stop normal reading at the detected reference boundary. Save progress after each completed section and checkpoint after each completed paper.
4. Record page, section, figure, or table references for important claims.
5. Report encrypted, corrupt, or scanned PDFs. Do not run OCR without explicit approval.
6. For every figure or table used in the explanation, call `inspect --page <n> --label <label>` first. It returns caption and vector/image-based `suggested_clip` as compact JSON without sending a page image into context.
7. When `inspect` returns one high-confidence match, call `render` once with that crop and visually inspect only the final PNG. Include axes, legends, subfigure labels, and caption. 不要先渲染或查看整页预览.
8. If the match is missing, ambiguous, low-confidence, or the final crop is incomplete, render one low-detail full-page fallback, adjust once, then keep only the final crop. Reuse an existing asset without rendering when its manifest source hash still matches.
9. Save local PNGs under `projects/<id>/assets/<citation_key>/`. 每个正文明确提到的图或表 must appear immediately beside its explanation in Markdown.
10. Keep a hidden `PAPERLAB:FIGURES` JSON comment in the AUTO block with source hash, page, clip, and relative asset path so missing local assets can be regenerated.
11. In the completion response, display only the most important one or two images inline and link the full note.

Use this narrative note shape. Adapt the explanation to the paper instead of filling a rigid checklist.

```markdown
# Paper title

> Authors｜Year｜Venue｜DOI｜Full-text evidence scope

<!-- PAPERLAB:AUTO:START -->

## 自动分析

### 一页读懂

Three to five connected paragraphs explaining the problem, approach, result, and significance.

### 问题与直觉

Explain why the problem matters, what prior approaches missed, and the concepts needed to follow the paper.

### 方法如何运作

Explain the data flow and causal logic. Place each cited figure beside its explanation and add a short 看图要点.

### 结果如何解释

Explain the core experiments with conditions, samples, units, pages, and figure or table numbers.

### 贡献、边界与下一步

Separate what is demonstrated, what is inferred, what remains uncertain, and what paper should be read next.

<details>
<summary>证据与复现速查</summary>

| 结论 | 证据类型 | 页码/图表 | 条件 |
|---|---|---|---|

Include parameters, reproduction requirements, and unresolved checks. Use 作者明确陈述、数据直接支持、合理推断、Codex 的解释、无法确认 as evidence types.

</details>

<!-- PAPERLAB:AUTO:END -->

## 人工确认

User-maintained content. Codex不得覆盖 this section.
```

When refreshing a note, replace only the AUTO block. Preserve everything else byte-for-byte. Write connected prose by default; use bullets only for parameters, procedures, or short limitations.

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
