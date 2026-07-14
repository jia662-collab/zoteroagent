# PDF Export Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every PaperLab PDF export reject raw LaTeX source, replacement characters, and blank pages before replacing the destination file.

**Architecture:** Keep the existing `export` command and temporary-file flow. Add one `validate_exported_pdf(path)` function beside `export_markdown_pdf`, call it on the temporary PDF, and update the paper-research export contract.

**Tech Stack:** Python standard library, existing PyMuPDF dependency, pytest.

## Global Constraints

- Add no command, configuration file, or dependency.
- Preserve atomic replacement: validation must run before `os.replace` or `os.link`.
- Do not modify source PDFs, Zotero data, manuscripts, or human-maintained sections.

---

### Task 1: Enforce PDF validation in the shared exporter

**Files:**
- Modify: `tests/test_pdf_export.py`
- Modify: `.paperlab/paperlab.py`
- Modify: `.agents/skills/paper-research/SKILL.md`

**Interfaces:**
- Consumes: a temporary PDF path produced by Chromium.
- Produces: `validate_exported_pdf(pdf: Path) -> int`, returning page count or raising `PaperLabError("export_validation_failed", message)`.

- [x] **Step 1: Write the failing test**

Add a test that creates a PDF containing literal `\frac{1}{N}`, loads the engine with `runpy.run_path`, calls `validate_exported_pdf`, and asserts `export_validation_failed`.

- [x] **Step 2: Run the test to verify RED**

Run: `python -m pytest -q tests/test_pdf_export.py::test_pdf_validation_rejects_raw_latex_source`

Expected: FAIL because `validate_exported_pdf` does not exist.

- [x] **Step 3: Implement the minimum validation**

Add `validate_exported_pdf(pdf: Path) -> int` that opens the PDF with PyMuPDF and rejects:

```python
raw_math = (r"\frac", r"\sum", r"\tag", r"\begin{", "$$", r"\left", r"\right")
```

It also rejects `\ufffd` and pages with no text, images, or drawings. Replace the existing page-count-only block in `export_markdown_pdf` with `page_count = validate_exported_pdf(pdf_path)`.

- [x] **Step 4: Update the workflow contract**

Extend export step 10 in `.agents/skills/paper-research/SKILL.md`: every export must pass the engine's automatic check before replacement or checkpoint; failures keep the existing PDF and must be reported.

- [x] **Step 5: Verify GREEN and regression safety**

Run:

```powershell
python -m pytest -q tests/test_pdf_export.py::test_pdf_validation_rejects_raw_latex_source
python -m pytest -q
```

Expected: the focused test passes and the full suite reports zero failures.

- [x] **Step 6: Verify real project artifacts**

Scan the 8 PDFs under `output/pdf/20260711_*` with PyMuPDF. Require exactly 8 files, no raw-math markers, no replacement characters, and no blank pages.

- [x] **Step 7: Commit**

```powershell
git add .paperlab/paperlab.py tests/test_pdf_export.py .agents/skills/paper-research/SKILL.md docs/superpowers/plans/2026-07-15-pdf-export-validation.md
git commit -m "fix: validate PaperLab PDF exports"
```
