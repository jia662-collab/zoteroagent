# Obsidian Voice Reflection Notes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给每个 CNN 知识点创建一份永不被自动覆盖的个人理解笔记，并从知识正文一键进入右侧 VoicePaste 文字记录工作流。

**Architecture:** 继续复用 `.paperlab/obsidian_vault.py` 的单一课程清单和幂等迁移流程。正式知识点链接由生成器维护；个人理解文件采用 write-once seed，已存在时完全跳过，从结构上保证语音文字不会被覆盖。

**Tech Stack:** Python 标准库、pytest、Obsidian 原生 Markdown/Properties/Search/Templates、VoicePaste Windows 桌面应用。

## Global Constraints

- 只保存文字，不创建或同步音频文件。
- 每个正式知识点恰好对应一份个人理解笔记。
- 个人理解只标记 `#reflection`，不得使用 `#knowledge`。
- 不安装新的 Obsidian 社区插件，不增加数据库、后台服务或自动分类。
- 自动流程只能创建缺失的个人理解文件，不能覆盖已经存在的文件。
- 模板不得包含“后续验证”。

---

### Task 1: 个人理解文件、入口和保护规则

**Files:**
- Modify: `.paperlab/obsidian_vault.py`
- Modify: `tests/test_obsidian_vault.py`

**Interfaces:**
- Produces: `reflection_path(module: str, index: int, title: str) -> str`
- Produces: `reflection_markdown(module: str, index: int, title: str) -> str`
- Produces: `reflection_seed_files() -> dict[str, str]`
- Changes: `lesson_auto_block(module: str, index: int, title: str) -> str`

- [ ] **Step 1: Write the failing bootstrap test**

Extend `test_bootstrap_creates_curated_three_level_structure_without_overwrite` with these assertions:

```python
reflection_root = vault / "10_深度学习与CNN" / "09_我的理解"
reflection_notes = sorted(reflection_root.glob("0[1-6]_*/*-我的理解.md"))
assert len(reflection_notes) == 45
for note in reflection_notes:
    text = note.read_text(encoding="utf-8")
    assert "type: reflection" in text
    assert "tags: [reflection]" in text
    assert "## 语音记录" in text
    assert "## 提炼后的理解" in text
    assert "后续验证" not in text
    assert "Win+H" not in text
    assert "VoicePaste" in text
```

Also assert each concept note contains its exact aliased reflection link.

- [ ] **Step 2: Run the test and verify RED**

Run:

```powershell
python -m pytest tests/test_obsidian_vault.py::test_bootstrap_creates_curated_three_level_structure_without_overwrite -q
```

Expected: FAIL because `09_我的理解` and its 45 files do not exist.

- [ ] **Step 3: Implement the minimum generator**

Add:

```python
REFLECTION_DIR = f"{SUBJECT}/09_我的理解"


def reflection_path(module: str, index: int, title: str) -> str:
    return f"{REFLECTION_DIR}/{module}/{index:02d}_{title}-我的理解.md"


def reflection_markdown(module: str, index: int, title: str) -> str:
    concept = concept_path(module, index, title)[:-3]
    return f'''---
type: reflection
concept: "[[{concept}]]"
status: 待提炼
tags: [reflection]
---

# 我的理解：{title}

## 语音记录

使用 VoicePaste 快捷键开始表达。

## 提炼后的理解

- 一句话理解：
- 我的例子：
- 与已有知识的联系：
- 仍然不明白：
'''


def reflection_seed_files() -> dict[str, str]:
    return {
        reflection_path(module, index, title): reflection_markdown(module, index, title)
        for module, concepts in KNOWLEDGE_MODULES.items()
        for index, (title, _) in enumerate(concepts, start=1)
    }
```

Change `lesson_auto_block` to accept `index` and append:

```python
## 我的理解

> [!tip] 个人语音笔记
> [[{reflection_path(module, index, title)[:-3]}|在右侧打开“我的理解”]]
```

Update its two callers. In `bootstrap_vault`, iterate over `{**generated_layout_files(), **reflection_seed_files()}` so existing files continue through `write_if_missing`.

In `migrate_vault_layout`, add only missing seed files to `planned`:

```python
for relative, default_text in reflection_seed_files().items():
    destination = vault / relative
    if not destination.exists():
        planned[destination] = default_text
```

- [ ] **Step 4: Verify GREEN and preservation**

Run the focused test, then add a sentence to one reflection note, run `bootstrap_vault` and `migrate_vault_layout`, and assert the entire file remains byte-for-byte identical.

- [ ] **Step 5: Commit**

```powershell
git add .paperlab/obsidian_vault.py tests/test_obsidian_vault.py
git commit -m "feat: add protected voice reflection notes"
```

---

### Task 2: 总览、模板和 VoicePaste 文案

**Files:**
- Modify: `.paperlab/obsidian_vault.py`
- Modify: `tests/test_obsidian_vault.py`
- Modify: `docs/superpowers/specs/2026-07-16-obsidian-voice-reflection-design.md`

**Interfaces:**
- Produces: `reflection_overview_markdown() -> str`
- Produces: `reflection_template_markdown() -> str`

- [ ] **Step 1: Write the failing overview/template test**

Add `test_bootstrap_adds_reflection_overview_and_core_template` asserting:

```python
overview = vault / "10_深度学习与CNN" / "09_我的理解" / "00_我的理解总览.md"
template = vault / "90_模板" / "个人理解模板.md"
overview_text = overview.read_text(encoding="utf-8")
template_text = template.read_text(encoding="utf-8")
assert "[status:待提炼]" in overview_text
assert "[status:已提炼]" in overview_text
assert "tag:#reflection" in overview_text
assert "{{date:YYYY-MM-DD}} {{time:HH:mm}}" in template_text
assert "VoicePaste" in template_text
assert "后续验证" not in template_text
```

- [ ] **Step 2: Run the test and verify RED**

Expected: FAIL because both files are missing.

- [ ] **Step 3: Implement two static native-Obsidian files**

`reflection_overview_markdown` returns two native Search query blocks scoped to `path:"10_深度学习与CNN/09_我的理解"` and `[status:待提炼]` / `[status:已提炼]`.

`reflection_template_markdown` returns the approved structure with:

```markdown
### {{date:YYYY-MM-DD}} {{time:HH:mm}}

使用 VoicePaste 快捷键开始表达。
```

Add both controlled files to `generated_layout_files`. Update the design document from `Win+H` to VoicePaste while retaining the no-audio requirement.

- [ ] **Step 4: Run focused tests**

Run:

```powershell
python -m pytest tests/test_obsidian_vault.py -q
```

Expected: all Obsidian Vault tests pass.

- [ ] **Step 5: Commit**

```powershell
git add .paperlab/obsidian_vault.py tests/test_obsidian_vault.py docs/superpowers/specs/2026-07-16-obsidian-voice-reflection-design.md
git commit -m "feat: add reflection dashboard and template"
```

---

### Task 3: 真实 Vault 迁移和验收

**Files:**
- Modify through the migration command: `E:\HuaweiMoveData\Users\XuJiasheng\Desktop\个人知识网络`

**Interfaces:**
- Consumes: `migrate_vault_layout`, `reflection_seed_files`, VoicePaste `2.1.3`
- Produces: 45 protected personal notes, one overview, one template, 45 concept links

- [ ] **Step 1: Run full automated verification**

```powershell
python -m pytest -q
python -m py_compile .paperlab\obsidian_vault.py
git diff --check
```

Expected: 0 failures and exit code 0.

- [ ] **Step 2: Dry-run and migrate the real Vault**

```powershell
python .paperlab\obsidian_vault.py migrate --vault "E:\HuaweiMoveData\Users\XuJiasheng\Desktop\个人知识网络" --dry-run
python .paperlab\obsidian_vault.py migrate --vault "E:\HuaweiMoveData\Users\XuJiasheng\Desktop\个人知识网络"
python .paperlab\obsidian_vault.py migrate --vault "E:\HuaweiMoveData\Users\XuJiasheng\Desktop\个人知识网络" --dry-run
```

Expected: final dry-run reports `moved: 0`, `rewritten: 0`, `removed: 0`.

- [ ] **Step 3: Validate the real artifacts**

Assert 45 reflection files, 45 concept links, unique concept frontmatter links, zero broken Wiki links, zero audio files under `09_我的理解`, and unchanged text after a second migration.

- [ ] **Step 4: Verify the desktop workflow**

Confirm VoicePaste `2.1.3` is running and responsive. In Obsidian, open `01_人工神经元与网络层`, follow the personal-note link, open it in a right split, and verify the VoicePaste instruction is visible. Do not record or save test audio.

- [ ] **Step 5: Finish the branch**

Run the full test suite after local merge, remove the owned `.worktrees` worktree, and preserve the unrelated user modification at `.agents/skills/paper-research/references/deep-reading.md`.
