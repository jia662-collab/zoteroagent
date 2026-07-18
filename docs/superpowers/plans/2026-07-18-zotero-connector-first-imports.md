# Connector-First Zotero Imports Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist and execute a Zotero import workflow that creates one parent item per paper, attaches PDFs beneath it, and exposes concise parent-item short titles.

**Architecture:** PaperLab remains the source of verified candidate URLs and the final readiness checker. Chrome and Zotero Connector create bibliographic parents and attachments in one operation; Zotero desktop supplies short titles, full-text fallback, and duplicate merging. RIS is generated only for individual failures.

**Tech Stack:** Python 3.11+, pytest, PaperLab CLI, Better BibTeX, Chrome, Zotero Connector, Zotero desktop.

## Global Constraints

- Never edit `zotero.sqlite` or Zotero `storage` directly.
- Save official paper landing pages, never raw PDF pages, when a candidate is not already in Zotero.
- Preserve the official `Title`; put concise names in `Short Title`.
- Process one paper at a time and verify each save before continuing.
- Use DOI first and normalized title second for deduplication.
- Use RIS only when Connector and DOI import both fail.
- Stop on login, paywall, or CAPTCHA; never bypass access controls.

---

### Task 1: Persist the Connector-first contract

**Files:**
- Modify: `.agents/skills/paper-research/SKILL.md`
- Modify: `README.md`
- Modify: `tests/test_skill_contract.py`

**Interfaces:**
- Consumes: approved design in `docs/superpowers/specs/2026-07-18-zotero-connector-first-import-design.md`
- Produces: repository instructions that prefer Connector and keep RIS as a fallback

- [ ] **Step 1: Write the failing contract test**

Add to `tests/test_skill_contract.py`:

```python
def test_skill_prefers_connector_and_preserves_parent_titles():
    text = SKILL.read_text(encoding="utf-8")
    for requirement in [
        "Zotero Connector",
        "正式论文页面",
        "Short Title",
        "查找全文",
        "RIS 只作为兜底",
    ]:
        assert requirement in text
    assert "不通过 Zotero Connector 保存裸 PDF 页面" in text
```

- [ ] **Step 2: Verify the test fails**

Run: `python -m pytest -q tests/test_skill_contract.py::test_skill_prefers_connector_and_preserves_parent_titles`

Expected: FAIL because the current skill still treats bulk RIS as the normal import path.

- [ ] **Step 3: Replace the import rules with the minimal workflow**

Rewrite only the `## Import to Zotero` section of `.agents/skills/paper-research/SKILL.md` so it requires this order:

```markdown
1. Run `sync --candidates` first and skip DOI/title matches already in Zotero.
2. For missing records, open the verified official paper landing page and save it with Zotero Connector.
3. Do not use Zotero Connector on a bare PDF page when a metadata parent exists.
4. Preserve the official `Title`; set a concise, unique `Short Title` such as `ResNet` or `BatchNorm`.
5. If the parent has no PDF, use Zotero “查找全文” on that existing parent.
6. If Connector fails, use DOI import; RIS 只作为兜底 for the individual remaining failure.
7. Never edit `zotero.sqlite` or Zotero `storage` directly.
```

Update the README import section to describe the same order and keep `zotero_import.ris` documented only as the fallback artifact.

- [ ] **Step 4: Run the contract suite**

Run: `python -m pytest -q tests/test_skill_contract.py`

Expected: all contract tests PASS.

- [ ] **Step 5: Commit the contract change**

```powershell
git add -- .agents/skills/paper-research/SKILL.md README.md tests/test_skill_contract.py
git commit -m "feat: prefer Connector for Zotero imports"
```

### Task 2: Establish the current Zotero baseline

**Files:**
- Read: `research/projects/20260711_深度学习_CNN/candidates.json`
- Read: `bibliography/library.bib`

**Interfaces:**
- Consumes: 21 verified candidates
- Produces: exact missing candidate IDs and existing duplicate sets

- [ ] **Step 1: Refresh the Better BibTeX index**

Run:

```powershell
python .paperlab\paperlab.py sync --bibtex bibliography\library.bib --index research\.paperlab\library_index.json --candidates research\projects\20260711_深度学习_CNN\candidates.json
```

Expected: JSON containing all 21 candidates with `ready`, `missing_pdf`, or `not_in_zotero` status.

- [ ] **Step 2: Keep only current failures**

Use the returned `matches` list. Browser import only records whose status is `not_in_zotero`; use Zotero full-text lookup only for `missing_pdf`; do nothing to `ready` records.

- [ ] **Step 3: Fix exact pre-existing duplicate sets**

In Zotero desktop, open “Duplicate Items”. Merge only DOI/title-confirmed duplicates reported by PaperLab. Select the metadata-complete version as master and retain all attachments.

### Task 3: Save missing papers through official landing pages

**Files:**
- Read: `research/projects/20260711_深度学习_CNN/candidates.json`

**Interfaces:**
- Consumes: current `not_in_zotero` records from Task 2
- Produces: one Zotero parent per candidate, with any accessible PDF as a child

- [ ] **Step 1: Verify Chrome, Zotero, and Connector are available**

Open the existing Chrome profile and Zotero desktop. Confirm the Connector icon is enabled and Zotero is responding before saving anything.

- [ ] **Step 2: Save each missing official landing page serially**

For each current missing candidate: open its verified `url`, confirm the page title, click Zotero Connector once, select the CNN research collection, and wait for the save popup to finish. Never click Connector from a raw PDF tab.

- [ ] **Step 3: Verify the parent immediately**

In Zotero, confirm exactly one new parent item matches the candidate DOI/title. If a PDF was available, confirm it appears below that parent. Stop that candidate if another parent was created.

- [ ] **Step 4: Use fallbacks without creating a second parent**

For an existing parent without a PDF, run “查找全文” on the parent. If no full text is available, leave the parent intact and record `missing_pdf`. If the landing page was not recognized, try DOI import; generate a single-record RIS only if DOI import also fails.

### Task 4: Add concise parent short titles

**Files:**
- Read: `research/projects/20260711_深度学习_CNN/candidates.json`

**Interfaces:**
- Consumes: the 21 matched Zotero parents
- Produces: unique `Short Title` values without changing official titles

- [ ] **Step 1: Set the short-title map**

Use these exact values in candidate order:

```text
CNN Survey, LeNet-5, AlexNet, VGG, GoogLeNet, ResNet, DenseNet,
MobileNet, EfficientNet, ConvNeXt, ConvNeXt V2, BatchNorm, Dropout,
Adam, Grad-CAM, FCN, U-Net, Faster R-CNN, ViT, SimCLR, Mask R-CNN
```

- [ ] **Step 2: Edit only `Short Title`**

For each matched parent in Zotero, set its `Short Title` to the mapped value. Do not alter `Title`, DOI, creators, year, publication, or attachments.

- [ ] **Step 3: Show the Short Title column**

Enable the Zotero “Short Title” column and position it beside the main Title column so the concise names remain visible.

### Task 5: Verify and checkpoint the batch

**Files:**
- Update via PaperLab: `research/projects/20260711_深度学习_CNN/STATUS.md`
- Update via PaperLab: `research/state/20260711_深度学习_CNN.json`

**Interfaces:**
- Consumes: updated Better BibTeX export after Zotero changes
- Produces: verified readiness counts and durable next action

- [ ] **Step 1: Wait for Better BibTeX and resync**

Run the Task 2 sync command again after `bibliography/library.bib` changes.

Expected: every saved parent is matched by DOI or normalized title; no new duplicate set exists.

- [ ] **Step 2: Validate the repository workflow**

Run:

```powershell
python -m pytest -q
git diff --check
```

Expected: all tests PASS and `git diff --check` reports no errors.

- [ ] **Step 3: Checkpoint the research project**

Run `checkpoint --backup` with only this batch's completed statement, remaining `missing_pdf` records, and the next reading action. Do not stage PDFs, BibTeX, caches, or Zotero data.
