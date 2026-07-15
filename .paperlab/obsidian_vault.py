from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


PAPERLAB_DIR = Path(__file__).resolve().parent
if str(PAPERLAB_DIR) not in sys.path:
    sys.path.insert(0, str(PAPERLAB_DIR))

from cnn_curriculum import FORMULAS, LABS, LESSONS, PAPER_ROADMAP


SUBJECT = "10_深度学习与CNN"
HOME_CANVAS = "00_首页/00_从这里开始.canvas"
PAPER_DIR = f"{SUBJECT}/07_论文与证据"
LAB_DIR = f"{SUBJECT}/08_实验项目"
REFLECTION_DIR = f"{SUBJECT}/09_我的理解"
HUMAN_PROMPT = "在这里记录你的理解、运行结果、错误样本和仍未解决的问题。工作流不会覆盖本节。"

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
    "04_经典与现代架构": [
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

LEGACY_MODULES = {"04_经典与现代架构": "04_其他网络架构"}

PAPER_WRAPPERS = {
    "01_LeNet": {
        "legacy": "论文-LeNet",
        "reading": "99_自动导入/精读稿/lecunGradientbasedLearningApplied1998",
        "translation": "99_自动导入/中文全文对照稿/lecunGradientbasedLearningApplied1998",
        "pdfs": ["LeNet_精读学习.pdf", "LeNet_中文全文对照.pdf"],
    },
    "02_AlexNet": {
        "legacy": "论文-AlexNet",
        "reading": "99_自动导入/精读稿/krizhevskyImageNetClassificationDeep2012",
        "translation": "99_自动导入/中文全文对照稿/krizhevskyImageNetClassificationDeep2012",
        "pdfs": ["AlexNet_精读学习.pdf", "AlexNet_中文全文对照.pdf"],
    },
    "03_VGG": {
        "legacy": "论文-VGG",
        "reading": "99_自动导入/精读稿/karensimonyanVeryDeepConvolutional2015",
        "translation": "99_自动导入/中文全文对照稿/karensimonyanVeryDeepConvolutional2015",
        "pdfs": ["VGG_精读学习.pdf", "VGG_中文全文对照.pdf"],
    },
    "04_CNN综述": {
        "legacy": "论文-CNN综述",
        "reading": "99_自动导入/精读稿/guRecentAdvancesConvolutional2018",
        "translation": "99_自动导入/中文全文对照稿/guRecentAdvancesConvolutional2018",
        "pdfs": ["CNN综述_精读学习.pdf", "CNN综述_中文全文对照.pdf"],
    },
}

PAPER_BY_CONCEPT = {
    "LeNet-5": "01_LeNet",
    "AlexNet": "02_AlexNet",
    "VGG": "03_VGG",
    "卷积运算": "04_CNN综述",
}

CATEGORIES = (
    ("精读稿", "papers", "*.md"),
    ("中文全文对照稿", "translations", "*.md"),
    ("证据卡", "evidence", "*.json"),
    ("PDF", None, "*.pdf"),
)

GRAPH_SETTINGS = {
    "search": "tag:#knowledge",
    "showTags": True,
    "showAttachments": False,
    "hideUnresolved": True,
    "showOrphans": False,
    "showArrow": True,
    "colorGroups": [
        {"query": "tag:#knowledge/module", "color": {"a": 1, "rgb": 3107738}},
        {"query": "tag:#knowledge/concept", "color": {"a": 1, "rgb": 3050327}},
        {"query": "tag:#knowledge/paper", "color": {"a": 1, "rgb": 8015531}},
    ],
}


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


def atomic_write_text(path: Path, text: str) -> None:
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


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_obsidian_markdown(text: str) -> str:
    """Use the MathJax delimiters that Obsidian renders reliably."""
    return text.replace(r"\(", "$").replace(r"\)", "$").replace(r"\[", "$$").replace(r"\]", "$$")


def canvas_id(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]


def file_node(
    path: str,
    x: int,
    y: int,
    width: int = 340,
    height: int = 170,
    color: str | None = None,
) -> dict[str, Any]:
    node: dict[str, Any] = {
        "id": canvas_id(path),
        "type": "file",
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "file": path,
    }
    if color:
        node["color"] = color
    return node


def text_node(text: str, x: int, y: int, width: int, height: int, color: str | None = None) -> dict[str, Any]:
    node: dict[str, Any] = {
        "id": canvas_id(f"text:{text}"),
        "type": "text",
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "text": text,
    }
    if color:
        node["color"] = color
    return node


def group_node(label: str, x: int, y: int, width: int, height: int) -> dict[str, Any]:
    return {
        "id": canvas_id(f"group:{label}"),
        "type": "group",
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "label": label,
    }


def edge(from_id: str, to_id: str, label: str = "") -> dict[str, Any]:
    result = {
        "id": f"edge-{canvas_id(f'{from_id}|{to_id}|{label}')}",
        "fromNode": from_id,
        "fromSide": "right",
        "toNode": to_id,
        "toSide": "left",
        "toEnd": "arrow",
    }
    if label:
        result["label"] = label
    return result


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def generated_content_equal(path: Path, current: str, expected: str) -> bool:
    if path.suffix not in {".canvas", ".json"}:
        return current == expected
    try:
        current_value = json.loads(current)
        expected_value = json.loads(expected)
    except (json.JSONDecodeError, TypeError):
        return current == expected
    if path.suffix == ".canvas":
        return all(current_value.get(key) == value for key, value in expected_value.items())
    return current_value == expected_value


def module_guide_path(module: str) -> str:
    return f"{SUBJECT}/{module}/00_{module[3:]}-导览.md"


def module_canvas_path(module: str) -> str:
    return f"{SUBJECT}/{module}/00_{module[3:]}.canvas"


def concept_path(module: str, index: int, title: str) -> str:
    return f"{SUBJECT}/{module}/{index:02d}_{title}.md"


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


def reflection_overview_markdown() -> str:
    return f'''---
type: overview
tags: [reflection]
---

# 我的理解

## 待提炼

```query
path:"{REFLECTION_DIR}" tag:#reflection [status:待提炼]
```

## 已提炼

```query
path:"{REFLECTION_DIR}" tag:#reflection [status:已提炼]
```
'''


def reflection_template_markdown() -> str:
    return '''---
type: reflection
concept: "[[]]"
status: 待提炼
tags: [reflection]
---

# 我的理解：{{title}}

## 语音记录

### {{date:YYYY-MM-DD}} {{time:HH:mm}}

使用 VoicePaste 快捷键开始表达。

## 提炼后的理解

- 一句话理解：
- 我的例子：
- 与已有知识的联系：
- 仍然不明白：
'''


def navigation_block(module: str, index: int, concepts: list[tuple[str, str]]) -> str:
    title = concepts[index - 1][0]
    previous = (
        f"[[{concept_path(module, index - 1, concepts[index - 2][0])[:-3]}]]"
        if index > 1
        else "无（本模块起点）"
    )
    following = (
        f"[[{concept_path(module, index + 1, concepts[index][0])[:-3]}]]"
        if index < len(concepts)
        else "无（本模块终点）"
    )
    return f"""<!-- knowledge-nav:start -->
路径：[[{module_guide_path(module)[:-3]}]] → {index:02d} {title}

上一节：{previous}<br>
下一节：{following}<br>
标签：#knowledge #knowledge/concept
<!-- knowledge-nav:end -->"""


def lab_note_path(lab_id: str) -> str:
    index = list(LABS).index(lab_id) + 1
    filename = LABS[lab_id].title.replace("/", "-")
    return f"{LAB_DIR}/{index:02d}_{filename}.md"


def lesson_auto_block(module: str, index: int, title: str) -> str:
    lesson = LESSONS[title]
    lab = f"\n关联实验：[[{lab_note_path(lesson.lab)[:-3]}]]\n" if lesson.lab else ""
    formula = f"\n## 公式与符号\n\n{FORMULAS[title]}\n" if title in FORMULAS else ""
    related_papers = [paper for paper in PAPER_ROADMAP if title in paper.concepts]
    recommendations = ""
    if related_papers:
        links = []
        for paper in related_papers:
            entry = paper.wrapper or f"[[{PAPER_DIR}/00_必读论文路线|{paper.title}]]"
            links.append(f"- {entry} — {paper.status}")
        recommendations = "\n## 推荐论文\n\n" + "\n".join(links) + "\n"
    checklist = "\n".join(f"- [ ] {item}" for item in lesson.checklist)
    return f'''<!-- KNOWLEDGE:AUTO:START -->

## 前情连接与本节目标

本节属于 [[{module_guide_path(module)[:-3]}]]。先明确输入输出、参数和数据形状，再判断该概念在模型中的作用。

## 一句话直觉

{lesson.intuition}

## 核心机制

{lesson.mechanism}
{formula}

## 具体例子

{lesson.worked_example}

## 在实际工作中的位置

{lesson.work_context}

## 练习或实验

{lesson.practice}
{lab}
## 证据与边界

{lesson.evidence}
{recommendations}

## 常见误区

{lesson.pitfalls}

## 学习检查

{checklist}

## 我的理解

> [!tip] 个人语音笔记
> [[{reflection_path(module, index, title)[:-3]}|在右侧打开“我的理解”]]

<!-- KNOWLEDGE:AUTO:END -->'''


def concept_markdown(module: str, index: int, concepts: list[tuple[str, str]]) -> str:
    title = concepts[index - 1][0]
    return f'''---
type: concept
status: 未学
module: "[[{module_guide_path(module)[:-3]}]]"
order: {index}
---

# {index:02d} {title}

{navigation_block(module, index, concepts)}

{lesson_auto_block(module, index, title)}

## 人工笔记

{HUMAN_PROMPT}
'''


def find_concept_path(title: str) -> str:
    for module, concepts in KNOWLEDGE_MODULES.items():
        for index, (concept, _) in enumerate(concepts, start=1):
            if concept == title:
                return concept_path(module, index, title)
    raise KeyError(title)


def lab_markdown(lab_id: str) -> str:
    lab = LABS[lab_id]
    related = [title for title, lesson in LESSONS.items() if lesson.lab == lab_id]
    concept_links = "\n".join(f"- [[{find_concept_path(title)[:-3]}]]" for title in related)
    return f'''---
type: lab
tags: [knowledge, knowledge/lab]
---

# {lab.title}

## 要回答的问题

{lab.question}

## 运行命令

```powershell
{lab.command}
```

## 预期观察

{lab.expected}

## 如何解释

{lab.interpretation}

## 适用边界

{lab.limitations}

## 关联概念

{concept_links}
'''


def module_markdown(module: str, concepts: list[tuple[str, str]]) -> str:
    links = "\n".join(
        f"{index}. [[{concept_path(module, index, title)[:-3]}]]"
        for index, (title, _) in enumerate(concepts, start=1)
    )
    return f'''---
type: module
tags: [knowledge, knowledge/module]
---

# {module[3:]}

## 学习目标

按顺序掌握本模块概念，并能解释相邻概念之间的关系。

## 学习顺序

{links}

## 完成标准

- [ ] 能串联解释本模块全部概念
- [ ] 能完成至少一个最小例子
- [ ] 能说出本模块与下一模块的连接
'''


def paper_markdown(title: str, record: dict[str, Any]) -> str:
    display = title.split("_", 1)[1]
    pdf_links = "\n".join(f"- [[99_自动导入/PDF/{name}]]" for name in record["pdfs"])
    concepts = []
    for module, entries in KNOWLEDGE_MODULES.items():
        for index, (concept, _) in enumerate(entries, start=1):
            if PAPER_BY_CONCEPT.get(concept) == title:
                concepts.append(f"- [[{concept_path(module, index, concept)[:-3]}]]")
    return f'''---
type: paper
status: 待复习
tags: [knowledge, knowledge/paper]
---

# {display}

## 支撑概念

{chr(10).join(concepts)}

## 阅读入口

- 精读稿：[[{record["reading"]}]]
- 中文全文对照稿：[[{record["translation"]}]]
{pdf_links}
'''


def paper_guide_markdown() -> str:
    links = "\n".join(f"- [[{PAPER_DIR}/{title}]]" for title in PAPER_WRAPPERS)
    return f'''---
type: overview
tags: [knowledge, knowledge/overview]
---

# 论文与证据

核心概念先从模块进入；论文用于核对原始证据和扩展阅读。

- [[{PAPER_DIR}/00_必读论文路线]]

{links}
'''


def paper_roadmap_markdown() -> str:
    headings = {
        "导航综述": "导航综述（1 篇）",
        "必读主线": "必读主线（12 篇）",
        "任务分支": "按任务必读（5 篇）",
        "扩展阅读": "扩展阅读（3 篇）",
    }
    sections = []
    for tier, heading in headings.items():
        rows = []
        papers = (paper for paper in PAPER_ROADMAP if paper.tier == tier)
        for index, paper in enumerate(papers, start=1):
            concepts = "、".join(
                f"[[{find_concept_path(title)[:-3]}|{title}]]" for title in paper.concepts
            )
            entry = paper.wrapper or f"[{paper.title}]({paper.url})"
            rows.append(
                f"### {index}. {paper.title}（{paper.year}）\n\n"
                f"- 作者：{paper.authors}\n"
                f"- 状态：**{paper.status}**\n"
                f"- 入口：{entry}\n"
                f"- 为什么读：{paper.role}\n"
                f"- 对应知识：{concepts}"
            )
        sections.append(f"## {heading}\n\n" + "\n\n".join(rows))
    return '''---
type: paper-roadmap
tags: [knowledge, knowledge/paper]
---

# CNN 必读论文路线

这不是按年份堆论文，而是按学习作用分层。**精读完成**表示本地已有全文精读与证据卡；**待导入与精读**只表示元数据和官方入口已核验，不能当作当前知识库的全文证据。

推荐顺序：LeNet → AlexNet → VGG → Inception → ResNet → BatchNorm → MobileNet → EfficientNet → ConvNeXt → ViT。任务论文在学到对应应用时插入。

''' + "\n\n".join(sections) + "\n"


def subject_markdown() -> str:
    links = "\n".join(f"- [[{module_guide_path(module)[:-3]}]]" for module in KNOWLEDGE_MODULES)
    return f'''---
type: overview
tags: [knowledge, knowledge/overview]
---

# 深度学习与卷积神经网络

从 [[{HOME_CANVAS}]] 开始，按模块编号依次学习。

{links}

- [[{PAPER_DIR}/00_论文导览]]
'''


def module_canvas(module: str, concepts: list[tuple[str, str]], module_index: int) -> dict[str, Any]:
    rows = min(len(concepts), 6)
    columns = 1 if len(concepts) <= 6 else 2
    width = 460 + columns * 400 + 440
    height = max(420, 190 + rows * 200)
    nodes: list[dict[str, Any]] = [group_node(module[3:], 0, 0, width, height)]
    guide = file_node(module_guide_path(module), 40, 70, color=str(module_index))
    nodes.append(guide)
    concept_nodes: list[dict[str, Any]] = []
    for index, (title, _) in enumerate(concepts, start=1):
        column = 0 if index <= 6 else 1
        row = (index - 1) % 6
        node = file_node(concept_path(module, index, title), 440 + column * 400, 70 + row * 200)
        nodes.append(node)
        concept_nodes.append(node)
    edges = [edge(guide["id"], concept_nodes[0]["id"], "开始")]
    edges.extend(edge(first["id"], second["id"]) for first, second in zip(concept_nodes, concept_nodes[1:]))

    papers = [PAPER_BY_CONCEPT[title] for title, _ in concepts if title in PAPER_BY_CONCEPT]
    for offset, paper in enumerate(papers):
        paper_node = file_node(f"{PAPER_DIR}/{paper}.md", 440 + columns * 400, 70 + offset * 200, color="5")
        nodes.append(paper_node)
        concept = next(title for title, mapped in PAPER_BY_CONCEPT.items() if mapped == paper)
        concept_index = next(index for index, (title, _) in enumerate(concepts) if title == concept)
        edges.append(edge(concept_nodes[concept_index]["id"], paper_node["id"], "论文证据"))
    return {"nodes": nodes, "edges": edges}


def home_canvas() -> dict[str, Any]:
    title = text_node(
        "# 从这里开始\n\n按 01 → 06 学习；论文是证据入口，不是主学习路径。",
        0,
        0,
        1540,
        180,
        "4",
    )
    nodes: list[dict[str, Any]] = [title]
    module_nodes: list[dict[str, Any]] = []
    for index, module in enumerate(KNOWLEDGE_MODULES, start=1):
        row, column = divmod(index - 1, 3)
        node = file_node(module_canvas_path(module), column * 400, 240 + row * 230, color=str(index))
        nodes.append(node)
        module_nodes.append(node)
    papers = file_node(f"{PAPER_DIR}/00_论文导览.md", 0, 730, 1540, 180, "5")
    nodes.append(papers)
    edges = [edge(first["id"], second["id"], "下一模块") for first, second in zip(module_nodes, module_nodes[1:])]
    return {"nodes": nodes, "edges": edges}


def graph_settings(existing: dict[str, Any] | None = None) -> dict[str, Any]:
    result = dict(existing or {})
    result.update(GRAPH_SETTINGS)
    return result


def generated_layout_files() -> dict[str, str]:
    usage = f'''# 使用说明

从 [[{HOME_CANVAS}]] 开始浏览。

- 首页负责选择模块，模块 Canvas 负责学习顺序，Markdown 负责正文。
- 全局图只显示带 `#knowledge` 标签的精选笔记。
- `99_自动导入` 是 PaperLab 生成副本，不要人工编辑。
- 学习状态使用：未学、学习中、已理解、待复习。
'''
    template = '''---
type: concept
status: 未学
---

# 概念名称

## 前情连接与本节目标
## 一句话直觉
## 核心机制
## 具体例子
## 在实际工作中的位置
## 练习或实验
## 证据与边界
## 常见误区
## 学习检查
## 人工笔记
'''
    files = {
        "00_首页/01_使用说明.md": usage,
        "90_模板/概念模板.md": template,
        "90_模板/个人理解模板.md": reflection_template_markdown(),
        f"{SUBJECT}/00_学科导览.md": subject_markdown(),
        f"{PAPER_DIR}/00_论文导览.md": paper_guide_markdown(),
        f"{PAPER_DIR}/00_必读论文路线.md": paper_roadmap_markdown(),
        f"{REFLECTION_DIR}/00_我的理解总览.md": reflection_overview_markdown(),
        f"{LAB_DIR}/cnn_labs.py": (PAPERLAB_DIR / "cnn_labs.py").read_text(encoding="utf-8"),
        HOME_CANVAS: json_text(home_canvas()),
    }
    for module_index, (module, concepts) in enumerate(KNOWLEDGE_MODULES.items(), start=1):
        files[module_guide_path(module)] = module_markdown(module, concepts)
        files[module_canvas_path(module)] = json_text(module_canvas(module, concepts, module_index))
        for index in range(1, len(concepts) + 1):
            files[concept_path(module, index, concepts[index - 1][0])] = concept_markdown(module, index, concepts)
    for title, record in PAPER_WRAPPERS.items():
        files[f"{PAPER_DIR}/{title}.md"] = paper_markdown(title, record)
    for lab_id in LABS:
        files[lab_note_path(lab_id)] = lab_markdown(lab_id)
    return files


def bootstrap_vault(vault: Path) -> dict[str, int]:
    vault = Path(vault)
    created = 0
    skipped = 0
    files = {**generated_layout_files(), **reflection_seed_files()}
    for relative, text in files.items():
        if write_if_missing(vault / relative, text):
            created += 1
        else:
            skipped += 1
    if write_if_missing(vault / ".obsidian" / "graph.json", json_text(graph_settings())):
        created += 1
    else:
        skipped += 1
    return {"created": created, "skipped": skipped, "vault": str(vault)}


def legacy_path_map(vault: Path) -> list[tuple[Path, Path]]:
    paths = [
        (vault / "00_首页" / "个人知识网络.canvas", vault / HOME_CANVAS),
        (vault / "00_首页" / "使用说明.md", vault / "00_首页" / "01_使用说明.md"),
        (vault / SUBJECT / "学科总览.md", vault / SUBJECT / "00_学科导览.md"),
    ]
    for module, concepts in KNOWLEDGE_MODULES.items():
        legacy_module = LEGACY_MODULES.get(module, module)
        old_root = vault / SUBJECT / legacy_module
        new_root = vault / SUBJECT / module
        paths.extend(
            [
                (old_root / "模块.canvas", vault / module_canvas_path(module)),
                (old_root / "模块总览.md", vault / module_guide_path(module)),
            ]
        )
        paths.extend(
            (old_root / f"{title}.md", vault / concept_path(module, index, title))
            for index, (title, _) in enumerate(concepts, start=1)
        )
    for title, record in PAPER_WRAPPERS.items():
        paths.append(
            (
                vault / SUBJECT / "90_论文证据" / f"{record['legacy']}.md",
                vault / PAPER_DIR / f"{title}.md",
            )
        )
    return paths


def legacy_wikilink_map() -> dict[str, str]:
    links = {
        "00_首页/个人知识网络": HOME_CANVAS.removesuffix(".canvas"),
        f"{SUBJECT}/学科总览": f"{SUBJECT}/00_学科导览",
    }
    for module, concepts in KNOWLEDGE_MODULES.items():
        legacy_module = LEGACY_MODULES.get(module, module)
        old_root = f"{SUBJECT}/{legacy_module}"
        links[f"{old_root}/模块总览"] = module_guide_path(module).removesuffix(".md")
        for index, (title, _) in enumerate(concepts, start=1):
            links[f"{old_root}/{title}"] = concept_path(module, index, title).removesuffix(".md")
    for title, record in PAPER_WRAPPERS.items():
        links[f"{SUBJECT}/90_论文证据/{record['legacy']}"] = f"{PAPER_DIR}/{title}"
    return links


def rewrite_legacy_wikilinks(text: str) -> str:
    links = legacy_wikilink_map()

    def replace(match: re.Match[str]) -> str:
        content = match.group(1)
        target_match = re.match(r"([^|#]+)(.*)", content, re.DOTALL)
        if not target_match:
            return match.group(0)
        target, suffix = target_match.groups()
        replacement = links.get(target.removesuffix(".md").removesuffix(".canvas"))
        return f"[[{replacement}{suffix}]]" if replacement else match.group(0)

    return re.sub(r"\[\[([^\]]+)\]\]", replace, text)


def extract_human_content(text: str, title: str, summary: str) -> tuple[str, bool]:
    if "## 人工笔记" in text:
        return text.split("## 人工笔记", 1)[1], True
    cleaned = re.sub(r"(?s)^---\n.*?\n---\n", "", text, count=1)
    cleaned = re.sub(r"<!-- knowledge-nav:start -->.*?<!-- knowledge-nav:end -->", "", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"<!-- KNOWLEDGE:AUTO:START -->.*?<!-- KNOWLEDGE:AUTO:END -->", "", cleaned, flags=re.DOTALL)
    ignored = {
        f"# {title}",
        f"# {re.escape(title)}",
        summary,
        "## 一句话理解",
        "## 为什么重要",
        "## 核心机制",
        "## 最小例子",
        "## 常见误区",
        "## 知识网络关系",
        "## 与其他概念的关系",
        "## 学习检查",
        "说明这个概念解决的问题，以及它在后续网络中的作用。",
        "用公式、数据形状或计算流程解释其工作方式。",
        "补充一个可以手算或运行的最小例子。",
        "记录最容易混淆的概念和适用边界。",
        "- [ ] 能用自己的话解释这个概念",
        "- [ ] 能说明它与前置知识的关系",
        "- [ ] 能完成一个最小例子",
    }
    retained: list[str] = []
    for line in cleaned.splitlines():
        stripped = line.strip()
        if not stripped:
            if retained and retained[-1] != "":
                retained.append("")
            continue
        if stripped in ignored or re.match(r"^# \d\d ", stripped):
            continue
        if stripped.startswith("- 属于：") or stripped.startswith("- 证据支持："):
            continue
        retained.append(line)
    return "\n".join(retained).strip(), False


def merge_concept_note(text: str, module: str, index: int, concepts: list[tuple[str, str]]) -> str:
    title, summary = concepts[index - 1]
    guide = module_guide_path(module)[:-3]
    human_content, has_human_section = extract_human_content(text, title, summary)
    if text.startswith("---\n") and "\n---\n" in text[4:]:
        end = text.find("\n---\n", 4)
        front = text[4:end].splitlines()
        module_found = False
        order_found = False
        for line_index, line in enumerate(front):
            if line.startswith("module:"):
                front[line_index] = f'module: "[[{guide}]]"'
                module_found = True
            elif line.startswith("order:"):
                front[line_index] = f"order: {index}"
                order_found = True
        if not module_found:
            front.append(f'module: "[[{guide}]]"')
        if not order_found:
            front.append(f"order: {index}")
        frontmatter = "---\n" + "\n".join(front) + "\n---"
    else:
        frontmatter = f'---\ntype: concept\nstatus: 未学\nmodule: "[[{guide}]]"\norder: {index}\n---'
    if has_human_section:
        human_section = "## 人工笔记" + human_content
    else:
        human_content = rewrite_legacy_wikilinks(human_content)
        human_section = f"## 人工笔记\n\n{human_content or HUMAN_PROMPT}\n"
    return (
        f"{frontmatter}\n\n# {index:02d} {title}\n\n"
        f"{navigation_block(module, index, concepts)}\n\n"
        f"{lesson_auto_block(module, index, title)}\n\n{human_section}"
    )


def migrate_vault_layout(vault: Path, dry_run: bool = False) -> dict[str, object]:
    vault = Path(vault)
    mappings = legacy_path_map(vault)
    conflicts = [destination for source, destination in mappings if source.exists() and destination.exists()]
    if conflicts:
        joined = ", ".join(str(path) for path in conflicts)
        raise FileExistsError(f"Migration destination already exists: {joined}")

    moves = [(source, destination) for source, destination in mappings if source.exists()]
    generated = generated_layout_files()
    planned: dict[Path, str] = {}
    source_for_destination = {destination: source for source, destination in moves}
    for relative, default_text in reflection_seed_files().items():
        destination = vault / relative
        if not destination.exists():
            planned[destination] = default_text
    for relative, default_text in generated.items():
        destination = vault / relative
        current_path = source_for_destination.get(destination, destination)
        current_text = current_path.read_text(encoding="utf-8") if current_path.exists() else ""
        if re.match(r"\d\d_.*\.md$", destination.name) and destination.parent.name.startswith("0"):
            module = destination.parent.name
            concepts = KNOWLEDGE_MODULES.get(module)
            if concepts and not destination.name.startswith("00_"):
                index = int(destination.name[:2])
                default_text = merge_concept_note(current_text or default_text, module, index, concepts)
        if not generated_content_equal(destination, current_text, default_text):
            planned[destination] = default_text

    graph_path = vault / ".obsidian" / "graph.json"
    existing_graph = json.loads(graph_path.read_text(encoding="utf-8")) if graph_path.exists() else {}
    graph_text = json_text(graph_settings(existing_graph))
    if not graph_path.exists() or not generated_content_equal(
        graph_path, graph_path.read_text(encoding="utf-8"), graph_text
    ):
        planned[graph_path] = graph_text

    obsolete = vault / SUBJECT / "00_总览.canvas"
    removals = [obsolete] if obsolete.exists() else []
    result: dict[str, object] = {
        "moved": len(moves),
        "rewritten": len(planned),
        "removed": len(removals),
        "conflicts": [],
        "backup_dir": "",
    }
    if dry_run or (not moves and not planned and not removals):
        return result

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_dir = vault / ".paperlab-backup" / timestamp
    backup_sources = {source for source, _ in moves}
    backup_sources.update(path for path in planned if path.exists() and path not in source_for_destination)
    backup_sources.update(removals)
    for path in sorted(backup_sources):
        target = backup_dir / path.relative_to(vault)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)

    for source, destination in moves:
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.replace(source, destination)
    for path, text in planned.items():
        atomic_write_text(path, text)
    for path in removals:
        path.unlink()

    for directory in [vault / SUBJECT / "90_论文证据", vault / SUBJECT / "04_其他网络架构"]:
        if directory.exists() and not any(directory.iterdir()):
            directory.rmdir()
    result["backup_dir"] = str(backup_dir)
    return result


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"files": []}
    return json.loads(path.read_text(encoding="utf-8"))


def sync_artifacts(project: Path, pdf_dir: Path, vault: Path) -> dict[str, object]:
    project = Path(project)
    pdf_dir = Path(pdf_dir)
    vault = Path(vault)
    import_root = vault / "99_自动导入"
    manifest_path = import_root / "_manifest.json"
    previous = load_manifest(manifest_path)
    previous_by_destination = {entry["destination"]: entry for entry in previous.get("files", [])}
    current: dict[str, dict[str, str]] = {}
    copied = 0
    unchanged = 0

    for category, project_subdir, pattern in CATEGORIES:
        source_dir = project / project_subdir if project_subdir else pdf_dir
        if not source_dir.exists():
            continue
        for source in sorted(source_dir.glob(pattern)):
            destination = import_root / category / source.name
            destination_relative = destination.relative_to(vault).as_posix()
            normalized_markdown = (
                rewrite_legacy_wikilinks(
                    normalize_obsidian_markdown(source.read_text(encoding="utf-8"))
                )
                if source.suffix.lower() == ".md"
                else None
            )
            source_hash = (
                hashlib.sha256(normalized_markdown.encode("utf-8")).hexdigest()
                if normalized_markdown is not None
                else file_sha256(source)
            )
            if destination.exists() and file_sha256(destination) == source_hash:
                unchanged += 1
            else:
                if normalized_markdown is not None:
                    atomic_write_text(destination, normalized_markdown)
                else:
                    atomic_copy(source, destination)
                copied += 1
            current[destination_relative] = {
                "source": str(source.resolve()),
                "destination": destination_relative,
                "sha256": source_hash,
                "status": "已同步",
            }

    stale_entries: list[dict[str, str]] = []
    for destination, entry in previous_by_destination.items():
        if destination not in current:
            stale = dict(entry)
            stale["status"] = "待同步"
            stale_entries.append(stale)

    files = sorted([*current.values(), *stale_entries], key=lambda entry: entry["destination"])
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    manifest = {"updated_at": timestamp, "files": files}
    atomic_write_text(manifest_path, json_text(manifest))
    status = f"# 同步状态\n\n- 更新时间：{timestamp}\n- 已同步：{len(current)}\n- 待同步：{len(stale_entries)}\n"
    atomic_write_text(import_root / "_同步状态.md", status)
    return {
        "copied": copied,
        "unchanged": unchanged,
        "stale": len(stale_entries),
        "import_root": str(import_root),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and sync the Obsidian knowledge vault")
    subparsers = parser.add_subparsers(dest="command", required=True)
    bootstrap = subparsers.add_parser("bootstrap")
    bootstrap.add_argument("--vault", type=Path, required=True)
    sync = subparsers.add_parser("sync")
    sync.add_argument("--project", type=Path, required=True)
    sync.add_argument("--pdf-dir", type=Path, required=True)
    sync.add_argument("--vault", type=Path, required=True)
    migrate = subparsers.add_parser("migrate")
    migrate.add_argument("--vault", type=Path, required=True)
    migrate.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "bootstrap":
        result = bootstrap_vault(args.vault)
    elif args.command == "sync":
        result = sync_artifacts(args.project, args.pdf_dir, args.vault)
    else:
        result = migrate_vault_layout(args.vault, dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
