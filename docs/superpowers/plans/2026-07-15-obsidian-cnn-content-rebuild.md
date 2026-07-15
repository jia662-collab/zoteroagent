# Obsidian CNN Content Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace 45 superficial CNN concept pages with substantive lessons, four runnable experiments, and evidence-grounded paper links while preserving user notes.

**Architecture:** Store lesson-specific teaching material in one curriculum module and keep the existing Vault generator responsible for frontmatter, navigation, controlled update blocks, migration, and links. Store the four experiments in one PyTorch CLI with a fast synthetic-data smoke mode; generated experiment notes explain full usage and limitations.

**Tech Stack:** Python standard library, PyTorch already available on the host, Markdown, Obsidian Canvas, pytest.

## Global Constraints

- Preserve the existing six-module, 45-concept structure and four paper wrappers.
- Never modify original research PDFs, Zotero storage, or `zotero.sqlite`.
- Only the controlled automatic block may be refreshed; preserve the human block byte-for-byte.
- Claims from LeNet, AlexNet, VGG, and the CNN review must include paper wrapper links and source page or figure/table anchors.
- Modern topics not established by the four papers must say `证据类型：教材性知识（当前四篇论文未直接覆盖）`.
- Do not add dependencies or require dataset downloads for smoke tests.

---

### Task 1: Define the curriculum content contract

**Files:**
- Create: `.paperlab/cnn_curriculum.py`
- Create: `tests/test_cnn_curriculum.py`

**Interfaces:**
- Produces: `LESSONS: dict[str, Lesson]`, `CORE_LESSONS: set[str]`, `LABS: dict[str, Lab]`, and `validate_curriculum() -> list[str]`.
- `Lesson` fields: `intuition`, `mechanism`, `worked_example`, `work_context`, `practice`, `evidence`, `pitfalls`, `checklist`, `lab`.
- `Lab` fields: `title`, `question`, `command`, `expected`, `interpretation`, `limitations`.

- [ ] **Step 1: Write the failing contract test**

Assert exactly 45 lessons, exactly four labs, no banned placeholder phrases, no empty required fields, every lesson has at least one concrete number/tensor shape/formula, every core lesson has a lab or runnable code reference, and every paper evidence claim contains a page/figure/table anchor.

- [ ] **Step 2: Run the contract test and verify RED**

Run: `python -m pytest tests/test_cnn_curriculum.py -q`

Expected: FAIL because `.paperlab/cnn_curriculum.py` does not exist.

- [ ] **Step 3: Add the curriculum schema and validator**

Use frozen dataclasses and ordinary dictionaries. `validate_curriculum()` returns readable errors instead of raising on the first problem so one run exposes the complete content gap.

- [ ] **Step 4: Add all 45 lesson records and four lab records**

Write concept-specific content for every existing title. Core notes explain formulas and tensor shapes in depth; support notes contain a concrete example and link to a relevant experiment. Evidence strings use only the four verified paper wrappers or the exact教材性知识 label.

- [ ] **Step 5: Run the contract test and verify GREEN**

Run: `python -m pytest tests/test_cnn_curriculum.py -q`

Expected: PASS.

### Task 2: Render controlled substantive lessons

**Files:**
- Modify: `.paperlab/obsidian_vault.py`
- Modify: `tests/test_obsidian_vault.py`

**Interfaces:**
- Consumes: `LESSONS`, `CORE_LESSONS`, and `LABS` from `cnn_curriculum.py`.
- Produces: `lesson_auto_block(module, index, title) -> str`, `merge_lesson_note(text, module, index, concepts) -> str`, and generated experiment notes under `10_深度学习与CNN/08_实验项目`.

- [ ] **Step 1: Write failing rendering tests**

Assert generated concept notes contain `KNOWLEDGE:AUTO` and `人工笔记` boundaries, real mechanism/example/work/practice/evidence/pitfall sections, and no placeholder prose. Assert all four experiment notes are generated and linked from relevant concepts.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `python -m pytest tests/test_obsidian_vault.py -q`

Expected: FAIL because the new controlled blocks and experiment notes are absent.

- [ ] **Step 3: Implement the minimal renderer**

Replace the placeholder `concept_markdown()` body with curriculum data. Keep frontmatter and the existing navigation helper. Add one automatic block and one human block; do not introduce a template engine.

- [ ] **Step 4: Implement merge semantics**

If a controlled block exists, replace it. If a legacy scaffold has no controlled block, retain non-scaffold user prose in the human section and replace the known scaffold. Re-running migration must produce zero rewrites.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run: `python -m pytest tests/test_obsidian_vault.py tests/test_cnn_curriculum.py -q`

Expected: PASS.

### Task 3: Add four runnable experiments

**Files:**
- Create: `.paperlab/cnn_labs.py`
- Create: `tests/test_cnn_labs.py`
- Modify: `.paperlab/obsidian_vault.py`

**Interfaces:**
- Produces CLI commands `autograd`, `activations`, `lenet`, and `vgg-ablation`, each supporting `--smoke`.
- Each command returns a small JSON-compatible result containing tensor shapes, loss/gradient or metric values, and the varied experimental factor.

- [ ] **Step 1: Write failing smoke tests**

Import each experiment function, run it with fixed seeds and synthetic tensors, and assert finite outputs, documented shapes, and the expected comparison field.

- [ ] **Step 2: Run the smoke tests and verify RED**

Run: `python -m pytest tests/test_cnn_labs.py -q`

Expected: FAIL because `.paperlab/cnn_labs.py` does not exist.

- [ ] **Step 3: Implement the four smallest experiments**

Use synthetic data for smoke mode. The full LeNet and VGG commands may use torchvision datasets when the user runs them, but must report the download requirement and never run a download during automated validation.

- [ ] **Step 4: Link commands and expected observations into experiment notes**

Copy the single lab script into the generated Vault experiment directory and link each experiment note to the concepts it tests and the applicable paper wrapper.

- [ ] **Step 5: Run smoke tests and verify GREEN**

Run: `python -m pytest tests/test_cnn_labs.py -q`

Expected: PASS without network access.

### Task 4: Migrate the real Vault safely

**Files:**
- Modify: `.paperlab/obsidian_vault.py`
- Modify: `tests/test_obsidian_vault.py`
- Update at runtime: `E:\HuaweiMoveData\Users\XuJiasheng\Desktop\个人知识网络`

**Interfaces:**
- Extends: `migrate_vault_layout(vault: Path, dry_run: bool = False) -> dict[str, object]`.

- [ ] **Step 1: Add failing preservation and idempotence tests**

Create one legacy scaffold note and one note containing user prose. Assert migration upgrades both, preserves user prose exactly, writes a backup, and returns zero changes on the second run.

- [ ] **Step 2: Run focused migration tests and verify RED**

Run: `python -m pytest tests/test_obsidian_vault.py -q`

Expected: FAIL because existing migration does not create controlled lesson blocks.

- [ ] **Step 3: Extend migration minimally**

Reuse the existing backup and atomic-write helpers. Detect only the known old scaffold sections; never discard unknown content.

- [ ] **Step 4: Run dry-run, migrate, sync, and rerun**

Run the migration once against the real Vault, sync the 20 paper artifacts, then run migration again.

Expected: first run reports rewrites and a backup path; second run reports zero moves, rewrites, and removals.

### Task 5: Verify and integrate

**Files:**
- Verify: repository and real Vault.

- [ ] **Step 1: Run full automated tests**

Run: `python -m pytest -q`

Expected: all tests pass.

- [ ] **Step 2: Run Vault acceptance checks**

Assert 45 substantive notes, four experiments, zero banned placeholders, zero broken Wiki/Canvas links, unchanged hashes for 20 paper artifacts, and unchanged original PDFs.

- [ ] **Step 3: Run Obsidian acceptance**

Open one core note, one support note, one experiment, and one paper PDF. Confirm formula rendering, code blocks, page-anchored evidence, navigation, and links. Return Obsidian to the home Canvas.

- [ ] **Step 4: Commit and merge locally**

Commit only the curriculum, lab, generator, tests, and plan changes. Preserve the unrelated existing edit to `.agents/skills/paper-research/references/deep-reading.md`. Merge the isolated feature branch into `codex/pdf-export-validation`, rerun tests, then remove the owned worktree.
