# Obsidian 个人知识网络 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在桌面建立独立的 Obsidian 个人知识网络 Vault，以深度学习与 CNN 为首个学科，并可重复、无损地接入现有 PaperLab 论文产物。

**Architecture:** 新增一个仅使用 Python 标准库的 `.paperlab/obsidian_vault.py`，负责首次生成 Markdown/JSON Canvas 和以后单向同步论文材料。知识正文保存在 Vault 的 Markdown 笔记中，Canvas 只保存布局和链接；PaperLab 始终是论文产物事实来源，自动导入区不接受人工编辑。

**Tech Stack:** Windows 11、PowerShell、Python 3、pytest、Obsidian 1.12.7、JSON Canvas 1.0、Advanced Canvas

## Global Constraints

- 新 Vault 固定为 `E:\HuaweiMoveData\Users\XuJiasheng\Desktop\个人知识网络`。
- 保留现有 Vault `E:\HuaweiMoveData\Users\XuJiasheng\Documents\Obsidian Vault`，不得修改或替换。
- 保留资料中心 `E:\HuaweiMoveData\Users\XuJiasheng\Desktop\深度学习CNN研究资料`。
- 不修改、移动、重命名、覆盖或删除 Zotero 原始 PDF、Zotero 数据库或 Zotero storage。
- PaperLab 项目固定为 `research/projects/20260711_深度学习_CNN`。
- PDF 导出目录固定为 `output/pdf/20260711_深度学习_CNN`。
- 只安装一个社区插件：Advanced Canvas；不安装 Excalibrain、Juggl 或其他图谱插件。
- 不重新安装当前已存在的 Obsidian 1.12.7。
- 只使用 Python 标准库；不修改 `requirements.txt`。
- 首次生成只创建缺失的人工知识文件，不覆盖用户后来编辑的笔记或 Canvas。
- 自动同步只覆盖 `99_自动导入` 中对应的生成副本，并使用临时文件加 `os.replace`，不产生半写入文件。

## File Structure

**Repository files**

- Create: `.paperlab/obsidian_vault.py` — 生成 Vault、JSON Canvas，并同步 PaperLab 产物。
- Create: `tests/test_obsidian_vault.py` — 验证重复生成、Canvas 合法性、原子复制和缺失源文件保留行为。

**Generated local Vault files**

- Create: `E:\HuaweiMoveData\Users\XuJiasheng\Desktop\个人知识网络\00_首页\个人知识网络.canvas`
- Create: `E:\HuaweiMoveData\Users\XuJiasheng\Desktop\个人知识网络\00_首页\使用说明.md`
- Create: `E:\HuaweiMoveData\Users\XuJiasheng\Desktop\个人知识网络\10_深度学习与CNN\00_总览.canvas`
- Create: six module folders under `10_深度学习与CNN`, each containing `模块总览.md`, `模块.canvas`, and concept notes.
- Create: four paper wrapper notes under `10_深度学习与CNN\90_论文证据`.
- Create: `90_模板\概念模板.md`.
- Create/update: `99_自动导入\{精读稿,中文全文对照稿,证据卡,PDF}` and `_manifest.json`, `_同步状态.md`.

---

### Task 1: Add the Repeatable Vault Builder and Artifact Sync

**Files:**

- Create: `.paperlab/obsidian_vault.py`
- Create: `tests/test_obsidian_vault.py`

**Interfaces:**

- Consumes: `Path` objects for a Vault root, PaperLab project root, and PDF export directory.
- Produces: `bootstrap_vault(vault: Path) -> dict[str, int]` and `sync_artifacts(project: Path, pdf_dir: Path, vault: Path) -> dict[str, object]`.
- CLI: `python .paperlab/obsidian_vault.py bootstrap --vault <path>` and `python .paperlab/obsidian_vault.py sync --project <path> --pdf-dir <path> --vault <path>`.

- [ ] **Step 1: Reconfirm the machine baseline before writing**

Run:

```powershell
Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*','HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*' -ErrorAction SilentlyContinue |
  Where-Object DisplayName -eq 'Obsidian' |
  Select-Object DisplayName,DisplayVersion,DisplayIcon
Get-Content -Raw "$env:APPDATA\obsidian\obsidian.json"
Get-ChildItem 'research\projects\20260711_深度学习_CNN\papers' -File
Get-ChildItem 'output\pdf\20260711_深度学习_CNN' -File
```

Expected: Obsidian `1.12.7`; the existing `Documents\Obsidian Vault` remains registered; four files appear in `papers`; eight PDF files appear in the export directory.

- [ ] **Step 2: Write the failing tests**

Create `tests/test_obsidian_vault.py` with these cases:

```python
from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / ".paperlab" / "obsidian_vault.py"
SPEC = importlib.util.spec_from_file_location("obsidian_vault", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_bootstrap_creates_complete_clickable_structure_without_overwrite(tmp_path: Path):
    vault = tmp_path / "个人知识网络"
    first = MODULE.bootstrap_vault(vault)

    assert first["created"] >= 60
    assert (vault / "00_首页" / "个人知识网络.canvas").exists()
    assert (vault / "10_深度学习与CNN" / "00_总览.canvas").exists()
    assert len(list((vault / "10_深度学习与CNN").glob("0?_*/*.canvas"))) == 6
    concept_notes = [
        path
        for path in (vault / "10_深度学习与CNN").glob("0?_*/*.md")
        if path.name != "模块总览.md"
    ]
    assert len(concept_notes) == 45

    for canvas_path in vault.rglob("*.canvas"):
        canvas = json.loads(canvas_path.read_text(encoding="utf-8"))
        node_ids = [node["id"] for node in canvas["nodes"]]
        assert len(node_ids) == len(set(node_ids))
        for node in canvas["nodes"]:
            if node["type"] == "file":
                assert (vault / node["file"]).exists(), (canvas_path, node["file"])

    edited = vault / "10_深度学习与CNN" / "03_卷积神经网络" / "卷积运算.md"
    edited.write_text("人工修改\n", encoding="utf-8")
    second = MODULE.bootstrap_vault(vault)
    assert second["created"] == 0
    assert edited.read_text(encoding="utf-8") == "人工修改\n"


def test_sync_is_idempotent_atomic_and_preserves_missing_sources(tmp_path: Path):
    project = tmp_path / "project"
    pdf_dir = tmp_path / "pdf"
    vault = tmp_path / "vault"
    samples = {
        project / "papers" / "paper.md": "精读",
        project / "translations" / "paper.md": "对照",
        project / "evidence" / "paper.json": "{}",
        pdf_dir / "paper.pdf": "%PDF-sample",
    }
    for path, content in samples.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    first = MODULE.sync_artifacts(project, pdf_dir, vault)
    assert first["copied"] == 4
    assert first["stale"] == 0
    assert not list(vault.rglob("*.tmp"))

    second = MODULE.sync_artifacts(project, pdf_dir, vault)
    assert second["copied"] == 0
    assert second["unchanged"] == 4

    removed = project / "papers" / "paper.md"
    removed.unlink()
    third = MODULE.sync_artifacts(project, pdf_dir, vault)
    preserved = vault / "99_自动导入" / "精读稿" / "paper.md"
    assert third["stale"] == 1
    assert preserved.read_text(encoding="utf-8") == "精读"
    manifest = json.loads((vault / "99_自动导入" / "_manifest.json").read_text(encoding="utf-8"))
    assert len({entry["destination"] for entry in manifest["files"]}) == 4
    assert any(entry["status"] == "待同步" for entry in manifest["files"])
```

- [ ] **Step 3: Run the tests and verify they fail**

Run:

```powershell
python -m pytest tests/test_obsidian_vault.py -q
```

Expected: collection fails because `.paperlab/obsidian_vault.py` does not exist.

- [ ] **Step 4: Implement the minimal standard-library tool**

Create `.paperlab/obsidian_vault.py`. Use these exact module and concept records as the knowledge tree:

```python
KNOWLEDGE_MODULES = {
    "01_数学与计算基础": [
        ("张量与线性代数", "理解标量、向量、矩阵、张量以及线性变换，是读懂网络数据流的基础。"),
        ("微积分与自动微分", "用导数、偏导数和链式法则解释梯度如何在计算图中传播。"),
        ("概率统计与信息论", "理解分布、期望、方差、最大似然、熵和交叉熵。"),
        ("优化与数值稳定性", "理解梯度下降、条件数、浮点误差、溢出和稳定计算。"),
    ],
    "02_神经网络基础": [
        ("人工神经元与网络层", "从加权求和与非线性变换理解神经元、层和网络。"),
        ("激活函数", "比较 sigmoid、tanh、ReLU、GELU 等非线性函数的作用与风险。"),
        ("前向传播与计算图", "跟踪输入如何经过参数化运算得到预测。"),
        ("损失函数", "理解分类、回归和表示学习目标如何转化为可优化标量。"),
        ("反向传播", "用链式法则计算每个参数对损失的影响。"),
        ("参数初始化与归一化", "理解初始化、BatchNorm、LayerNorm 对信号和梯度的影响。"),
        ("正则化", "理解权重衰减、Dropout、早停等控制泛化误差的方法。"),
    ],
    "03_卷积神经网络": [
        ("图像与特征图表示", "理解批次、通道、高度、宽度以及特征图的语义。"),
        ("卷积运算", "理解卷积核滑动、局部加权求和和输出尺寸计算。"),
        ("局部连接与权重共享", "理解 CNN 如何利用图像的局部结构并减少参数量。"),
        ("填充步幅与空洞卷积", "理解 padding、stride、dilation 如何改变分辨率与采样范围。"),
        ("感受野", "区分理论感受野与有效感受野，并计算层叠卷积的覆盖范围。"),
        ("池化与下采样", "理解最大池化、平均池化和带步幅卷积的取舍。"),
        ("通道与特征层级", "理解浅层纹理、深层语义以及通道混合。"),
        ("1x1分组与深度可分离卷积", "理解 1x1、group、depthwise separable convolution 的结构和效率。"),
    ],
    "04_其他网络架构": [
        ("LeNet-5", "理解早期 CNN 的卷积、下采样和分类器组合。"),
        ("AlexNet", "理解 ReLU、Dropout、数据增强和 GPU 训练带来的突破。"),
        ("VGG", "理解重复小卷积核和加深网络的统一设计。"),
        ("Inception", "理解多尺度并行分支与 1x1 瓶颈。"),
        ("ResNet", "理解残差连接如何改善深层网络优化。"),
        ("DenseNet", "理解密集连接、特征复用和梯度流。"),
        ("MobileNet与EfficientNet", "理解轻量卷积、复合缩放和移动端效率。"),
        ("ConvNeXt", "理解现代化纯卷积网络如何吸收 Transformer 设计经验。"),
        ("U-Net", "理解编码器、解码器和跳跃连接在像素级预测中的作用。"),
    ],
    "05_训练与评估": [
        ("数据集划分与数据泄漏", "正确区分训练、验证、测试集合并防止信息泄漏。"),
        ("数据增强", "理解几何、颜色、混合类增强及其适用边界。"),
        ("优化器与学习率", "比较 SGD、Momentum、Adam 和学习率调度。"),
        ("分类指标与混淆矩阵", "理解 accuracy、precision、recall、F1、ROC-AUC 和类别不平衡。"),
        ("过拟合欠拟合与泛化", "从训练曲线诊断容量、数据和正则化问题。"),
        ("调试与可复现性", "建立种子、日志、检查点、消融实验和错误分析习惯。"),
        ("迁移学习与微调", "理解预训练特征、冻结策略、领域偏移和小数据训练。"),
    ],
    "06_应用与前沿": [
        ("图像分类", "从输入图像预测一个或多个类别。"),
        ("目标检测", "同时完成目标定位与类别判断。"),
        ("语义与实例分割", "理解像素级分类和实例区分。"),
        ("OCR与文档理解", "连接视觉特征、字符序列和版面结构。"),
        ("医学影像与遥感", "理解高分辨率、小样本、标注成本和领域风险。"),
        ("视频与三维视觉", "把空间卷积扩展到时间、深度和点云。"),
        ("自监督与表征学习", "在有限标签条件下学习可迁移视觉表示。"),
        ("CNN与Transformer混合", "比较局部归纳偏置、全局建模和混合骨干网络。"),
        ("模型压缩与部署", "理解剪枝、量化、蒸馏、ONNX 和推理性能。"),
        ("鲁棒性可解释性与安全", "理解分布偏移、对抗样本、显著性图和可靠性边界。"),
    ],
}
```

The implementation must follow these exact behaviors:

```python
def write_if_missing(path: Path, text: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        return True
    except FileExistsError:
        return False


def atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(descriptor)
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
```

`bootstrap_vault` must:

1. Create `00_首页`, `10_深度学习与CNN`, `90_模板`, and `99_自动导入`.
2. Render one non-empty concept note per `KNOWLEDGE_MODULES` entry with frontmatter properties `type: concept`, `status: 未学`, and `module`.
3. Render each module's `模块总览.md` with links to every concept in that module.
4. Render four non-empty paper wrapper notes named `论文-LeNet.md`, `论文-AlexNet.md`, `论文-VGG.md`, and `论文-CNN综述.md`, linking respectively to the matching imported reading note and PDFs.
5. Render eight valid JSON Canvas files: one home Canvas, one subject Canvas, and six module Canvases.
6. Use only JSON Canvas 1.0 keys: `nodes`, `edges`, file/group node fields, and labeled edges.
7. Place native group nodes around module contents so Advanced Canvas can collapse them after installation.
8. Use `write_if_missing` for all manually editable Markdown and Canvas files.

Use this exact paper-wrapper mapping; wrapper links must use Vault-relative paths without `.md` on Markdown wikilinks:

```python
PAPER_WRAPPERS = {
    "论文-LeNet": {
        "reading": "99_自动导入/精读稿/lecunGradientbasedLearningApplied1998",
        "translation": "99_自动导入/中文全文对照稿/lecunGradientbasedLearningApplied1998",
        "pdfs": ["LeNet_精读学习.pdf", "LeNet_中文全文对照.pdf"],
    },
    "论文-AlexNet": {
        "reading": "99_自动导入/精读稿/krizhevskyImageNetClassificationDeep2012",
        "translation": "99_自动导入/中文全文对照稿/krizhevskyImageNetClassificationDeep2012",
        "pdfs": ["AlexNet_精读学习.pdf", "AlexNet_中文全文对照.pdf"],
    },
    "论文-VGG": {
        "reading": "99_自动导入/精读稿/karensimonyanVeryDeepConvolutional2015",
        "translation": "99_自动导入/中文全文对照稿/karensimonyanVeryDeepConvolutional2015",
        "pdfs": ["VGG_精读学习.pdf", "VGG_中文全文对照.pdf"],
    },
    "论文-CNN综述": {
        "reading": "99_自动导入/精读稿/guRecentAdvancesConvolutional2018",
        "translation": "99_自动导入/中文全文对照稿/guRecentAdvancesConvolutional2018",
        "pdfs": ["CNN综述_精读学习.pdf", "CNN综述_中文全文对照.pdf"],
    },
}
```

Canvas generation must be deterministic:

- Generate node IDs as `hashlib.sha1(vault_relative_path.encode("utf-8")).hexdigest()[:12]`; prefix edge IDs with `edge-`.
- Home Canvas contains one file node for `10_深度学习与CNN/00_总览.canvas`.
- Subject Canvas contains six group nodes and one module-Canvas file node inside each group.
- Each module Canvas contains one group node, one `模块总览.md` file node, and every concept file node for that module.
- Lay out concept nodes in a three-column grid using width `320`, height `180`, horizontal gap `40`, and vertical gap `40`.
- Create a labeled `组成` edge from the module overview node to every concept node.
- Store JSON with `ensure_ascii=False`, `indent=2`, UTF-8, and a trailing newline.

Use this note body for every concept, replacing values from the seed:

```markdown
---
type: concept
status: 未学
module: "[[模块总览]]"
---

# {title}

## 一句话理解

{summary}

## 知识网络关系

- 属于：[[模块总览]]

## 学习检查

- [ ] 能用自己的话解释这个概念
- [ ] 能说明它与前置知识的关系
- [ ] 能完成一个最小例子
```

`sync_artifacts` must map sources exactly as follows:

```python
CATEGORIES = (
    ("精读稿", "papers", "*.md"),
    ("中文全文对照稿", "translations", "*.md"),
    ("证据卡", "evidence", "*.json"),
    ("PDF", None, "*.pdf"),
)
```

For each source file, calculate SHA-256. Skip a destination with the same hash; otherwise copy with `atomic_copy`. Store `source`, `destination`, `sha256`, and `status` in `99_自动导入/_manifest.json`. If an entry from the previous manifest no longer has a source file, keep its destination and manifest entry with `status: 待同步`. Write `_manifest.json` and `_同步状态.md` atomically only after all file copies finish.

- [ ] **Step 5: Run the focused tests**

Run:

```powershell
python -m pytest tests/test_obsidian_vault.py -q
```

Expected: `2 passed` and no `.tmp` files.

- [ ] **Step 6: Run the full repository test suite**

Run:

```powershell
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 7: Commit the reusable tool**

```powershell
git add .paperlab/obsidian_vault.py tests/test_obsidian_vault.py
git commit -m "feat: build and sync Obsidian knowledge vault"
```

Expected: the commit contains only the two files above; the pre-existing modification to `.agents/skills/paper-research/references/deep-reading.md` remains unstaged.

---

### Task 2: Bootstrap the Real Personal Knowledge Vault

**Files:**

- Create: `E:\HuaweiMoveData\Users\XuJiasheng\Desktop\个人知识网络\**`
- Preserve: `E:\HuaweiMoveData\Users\XuJiasheng\Documents\Obsidian Vault\**`

**Interfaces:**

- Consumes: `bootstrap_vault(vault)` from Task 1.
- Produces: eight Canvas files, 45 concept notes, six module index notes, four paper wrapper notes, one template, and one usage note.

- [ ] **Step 1: Verify the target is safe**

Run:

```powershell
$vault='E:\HuaweiMoveData\Users\XuJiasheng\Desktop\个人知识网络'
if (Test-Path $vault) {
  Get-ChildItem -Force $vault
} else {
  'target_absent'
}
```

Expected: `target_absent`, or only files created by an earlier incomplete attempt. If unrelated user files exist, stop before writing and report them.

- [ ] **Step 2: Generate the Vault**

Run:

```powershell
python .paperlab\obsidian_vault.py bootstrap --vault 'E:\HuaweiMoveData\Users\XuJiasheng\Desktop\个人知识网络'
```

Expected JSON: `created` is at least `60` on the first run and `skipped` is `0`.

- [ ] **Step 3: Prove generation is idempotent**

Run the same command again.

Expected JSON: `created` is `0`; existing Markdown and Canvas files remain byte-for-byte unchanged.

- [ ] **Step 4: Validate structure and Canvas JSON**

Run:

```powershell
@'
import json
from pathlib import Path

vault = Path(r'E:\HuaweiMoveData\Users\XuJiasheng\Desktop\个人知识网络')
canvases = list(vault.rglob('*.canvas'))
concepts = [p for p in (vault / '10_深度学习与CNN').glob('0?_*/*.md') if p.name != '模块总览.md']
assert len(canvases) == 8, len(canvases)
assert len(concepts) == 45, len(concepts)
for path in canvases:
    data = json.loads(path.read_text(encoding='utf-8'))
    ids = [n['id'] for n in data['nodes']]
    assert len(ids) == len(set(ids)), path
    for node in data['nodes']:
        if node['type'] == 'file':
            assert (vault / node['file']).exists(), (path, node['file'])
print({'canvases': len(canvases), 'concepts': len(concepts)})
'@ | python -
```

Expected: `{'canvases': 8, 'concepts': 45}`.

---

### Task 3: Import the Current Four Papers and Eight PDFs

**Files:**

- Read: `research/projects/20260711_深度学习_CNN/{papers,translations,evidence}`
- Read: `output/pdf/20260711_深度学习_CNN`
- Create/update: `E:\HuaweiMoveData\Users\XuJiasheng\Desktop\个人知识网络\99_自动导入\**`

**Interfaces:**

- Consumes: `sync_artifacts(project, pdf_dir, vault)` from Task 1.
- Produces: 4 reading notes, 4 bilingual notes, 4 evidence cards, 8 PDFs, one manifest, and one sync-status note.

- [ ] **Step 1: Record source hashes before syncing**

Run:

```powershell
$sources=@(
  'research\projects\20260711_深度学习_CNN\papers',
  'research\projects\20260711_深度学习_CNN\translations',
  'research\projects\20260711_深度学习_CNN\evidence',
  'output\pdf\20260711_深度学习_CNN'
)
Get-ChildItem $sources -File | Get-FileHash -Algorithm SHA256 | Sort-Object Path | Export-Csv "$env:TEMP\obsidian-source-before.csv" -NoTypeInformation -Encoding UTF8
```

Expected: 20 source hash records.

- [ ] **Step 2: Run the one-way sync**

Run:

```powershell
python .paperlab\obsidian_vault.py sync `
  --project 'research\projects\20260711_深度学习_CNN' `
  --pdf-dir 'output\pdf\20260711_深度学习_CNN' `
  --vault 'E:\HuaweiMoveData\Users\XuJiasheng\Desktop\个人知识网络'
```

Expected JSON: `stale` is `0`; the manifest contains 20 unique destinations.

- [ ] **Step 3: Verify exact import counts and links**

Run:

```powershell
$root='E:\HuaweiMoveData\Users\XuJiasheng\Desktop\个人知识网络\99_自动导入'
@{
  readings=(Get-ChildItem "$root\精读稿" -Filter *.md -File).Count
  translations=(Get-ChildItem "$root\中文全文对照稿" -Filter *.md -File).Count
  evidence=(Get-ChildItem "$root\证据卡" -Filter *.json -File).Count
  pdfs=(Get-ChildItem "$root\PDF" -Filter *.pdf -File).Count
  manifest=((Get-Content -Raw "$root\_manifest.json" | ConvertFrom-Json).files.destination | Sort-Object -Unique).Count
}
```

Expected: `readings=4`, `translations=4`, `evidence=4`, `pdfs=8`, `manifest=20`.

- [ ] **Step 4: Verify source files were not changed**

Run the same source hash command into `$env:TEMP\obsidian-source-after.csv`, then:

```powershell
Compare-Object (Import-Csv "$env:TEMP\obsidian-source-before.csv") (Import-Csv "$env:TEMP\obsidian-source-after.csv") -Property Path,Hash
```

Expected: no output.

- [ ] **Step 5: Re-run sync**

Run the Task 3 Step 2 command again.

Expected JSON: `copied=0`, `unchanged=20`, `stale=0`; no duplicate files appear.

---

### Task 4: Register the Vault, Enable One Plugin, and Perform End-to-End QA

**Files:**

- Modify through Obsidian UI only: `%APPDATA%\obsidian\obsidian.json` registration state and the new Vault's `.obsidian` settings.
- Preserve: all files under the existing `Documents\Obsidian Vault`.

**Interfaces:**

- Consumes: the generated Vault and imported artifacts from Tasks 2 and 3.
- Produces: a registered Obsidian Vault with Advanced Canvas enabled and verified fallback behavior.

- [ ] **Step 1: Open the installed Obsidian executable**

Run:

```powershell
Start-Process 'D:\Download\Obsidian\Obsidian.exe'
```

Expected: Obsidian opens. Do not reinstall or update it during this task.

- [ ] **Step 2: Register the new Vault without replacing the old Vault**

In Obsidian, choose **Open folder as vault** and select:

`E:\HuaweiMoveData\Users\XuJiasheng\Desktop\个人知识网络`

Expected: the Vault switcher contains both `Obsidian Vault` and `个人知识网络`.

- [ ] **Step 3: Enable only required core features**

In **Settings → Core plugins**, verify Canvas, Graph view, Backlinks, Properties, Templates, and Command palette are enabled.

Expected: `00_首页/个人知识网络.canvas` opens and all file nodes can be clicked before any community plugin is enabled.

- [ ] **Step 4: Install and enable Advanced Canvas**

In **Settings → Community plugins**, enable community plugins, select **Browse**, search `Advanced Canvas`, install it, and enable it.

Expected: the command palette contains `Advanced Canvas: Toggle collapse group`. No second community plugin is installed for this project.

- [ ] **Step 5: Verify the complete click path**

Open `00_首页/个人知识网络.canvas` and verify:

1. Home Canvas → `10_深度学习与CNN/00_总览.canvas`.
2. Subject Canvas → `03_卷积神经网络/模块.canvas`.
3. Module Canvas → `卷积运算.md`.
4. Concept note → module backlink/local graph.
5. Architecture module → one of `论文-LeNet.md`, `论文-AlexNet.md`, or `论文-VGG.md`.
6. Paper wrapper → imported reading note and PDF.

Expected: every step opens the intended local file; the PDF renders inside Obsidian.

- [ ] **Step 6: Verify collapsible groups and local graph**

Select a group in a module Canvas and run `Advanced Canvas: Toggle collapse group` twice.

Expected: the group collapses and expands without losing nodes or edges. Open a concept note's local graph and move the depth slider through 1, 2, and 3.

- [ ] **Step 7: Verify fallback without Advanced Canvas**

Temporarily disable Advanced Canvas and reopen the home and module Canvas files.

Expected: native Canvas, file-node navigation, Markdown links, backlinks, and local graph remain usable. Re-enable Advanced Canvas after verification.

- [ ] **Step 8: Final filesystem verification**

Run:

```powershell
python -m pytest tests/test_obsidian_vault.py -q
git status --short
Get-Content -Raw "$env:APPDATA\obsidian\obsidian.json"
```

Expected: focused tests pass; both Vault paths are registered; the only pre-existing unrelated worktree change remains `.agents/skills/paper-research/references/deep-reading.md` unless Task 1's tool commit is intentionally present in history.

## References

- [Obsidian Canvas](https://obsidian.md/help/plugins/canvas)
- [Obsidian Graph view](https://obsidian.md/help/plugins/graph)
- [JSON Canvas 1.0 specification](https://jsoncanvas.org/spec/1.0/)
- [Advanced Canvas](https://github.com/Developer-Mike/obsidian-advanced-canvas)
