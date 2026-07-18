# Bilingual PDF Publisher Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every PaperLab PDF use the approved A publisher layout and eliminate formula and obsolete human-confirmation defects before final export.

**Architecture:** Keep one export path in `.paperlab/paperlab.py`. Add semantic HTML around existing bilingual heading pairs, style it with the existing embedded CSS, and retain the current Chromium/PyMuPDF export and validation path.

**Tech Stack:** Python standard library, Markdown, Matplotlib mathtext, Chromium, PyMuPDF, pytest.

## Global Constraints

- Do not modify source PDFs or Zotero storage.
- Do not add a template engine or another runtime dependency.
- Do not export the ten final PDFs until the shared engine and AlexNet proof pass.

---

### Task 1: Semantic publisher HTML and formula delimiter fix

**Files:**
- Modify: `.paperlab/paperlab.py`
- Test: `tests/test_pdf_export.py`

**Interfaces:**
- Consumes: `markdown_document(source: Path, kind: str, text: str | None = None) -> str`
- Produces: semantic `bilingual-pair`, `source-text`, and `translation-text` HTML plus safe inline-math recognition.

- [ ] Add a failing HTML test that requires the approved A classes, publisher CSS, running header, and no human-confirmation heading.
- [ ] Run `python -m pytest tests/test_pdf_export.py -k publisher -q` and confirm it fails on missing classes.
- [ ] Add a failing math test with `$256\\times256$` on both sides of Chinese prose and `paid $5 and $10` as literal currency.
- [ ] Run the focused math test and confirm the current parser captures prose or alters currency.
- [ ] Implement the smallest shared HTML grouping, CSS, header/footer, and inline-math guard.
- [ ] Run `python -m pytest tests/test_pdf_export.py -q` and confirm all export tests pass without warnings.

### Task 2: Workflow contract and final artifacts

**Files:**
- Modify: `.agents/skills/paper-research/SKILL.md`
- Modify: `.agents/skills/paper-research/references/deep-reading.md`
- Modify: `README.md`
- Modify: `tests/test_skill_contract.py`
- Regenerate: `output/pdf/20260711_深度学习_CNN/*.pdf`

**Interfaces:**
- Consumes: the shared exporter from Task 1.
- Produces: ten validated PDFs and matching Obsidian copies without an artificial confirmation section.

- [ ] Run the AlexNet translation and learning exports to temporary PDF paths.
- [ ] Render representative AlexNet pages and inspect typography, bilingual hierarchy, equations, figures, references, header, and page number.
- [ ] Run the full test suite and confirm zero failures and zero export warnings.
- [ ] Export all ten PDFs once with `--replace`.
- [ ] Verify PDF text contains no `人工确认`, raw LaTeX, replacement characters, or blank pages.
- [ ] Copy the validated Markdown and PDFs to Obsidian and verify hashes match.
