from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


SUBJECT = "10_深度学习与CNN"

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

PAPER_BY_CONCEPT = {
    "LeNet-5": "论文-LeNet",
    "AlexNet": "论文-AlexNet",
    "VGG": "论文-VGG",
    "卷积运算": "论文-CNN综述",
}

CATEGORIES = (
    ("精读稿", "papers", "*.md"),
    ("中文全文对照稿", "translations", "*.md"),
    ("证据卡", "evidence", "*.json"),
    ("PDF", None, "*.pdf"),
)


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


def canvas_id(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]


def file_node(path: str, x: int, y: int, width: int = 320, height: int = 180, color: str | None = None) -> dict[str, Any]:
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


def edge(from_id: str, to_id: str, label: str) -> dict[str, Any]:
    return {
        "id": f"edge-{canvas_id(f'{from_id}|{to_id}|{label}')}",
        "fromNode": from_id,
        "fromSide": "right",
        "toNode": to_id,
        "toSide": "left",
        "toEnd": "arrow",
        "label": label,
    }


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def concept_markdown(module: str, title: str, summary: str) -> str:
    module_link = f"{SUBJECT}/{module}/模块总览"
    evidence = ""
    if title in PAPER_BY_CONCEPT:
        evidence = f"- 证据支持：[[{SUBJECT}/90_论文证据/{PAPER_BY_CONCEPT[title]}]]\n"
    return f'''---
type: concept
status: 未学
module: "[[{module_link}]]"
---

# {title}

## 一句话理解

{summary}

## 知识网络关系

- 属于：[[{module_link}]]
{evidence}
## 学习检查

- [ ] 能用自己的话解释这个概念
- [ ] 能说明它与前置知识的关系
- [ ] 能完成一个最小例子
'''


def module_markdown(module: str, concepts: list[tuple[str, str]]) -> str:
    links = "\n".join(f"- [[{SUBJECT}/{module}/{title}]]" for title, _ in concepts)
    return f"# {module[3:]}\n\n## 概念入口\n\n{links}\n"


def paper_markdown(title: str, record: dict[str, Any]) -> str:
    pdf_links = "\n".join(f"- [[99_自动导入/PDF/{name}]]" for name in record["pdfs"])
    return f'''---
type: paper
status: 待复习
---

# {title}

## 本地材料

- 精读稿：[[{record["reading"]}]]
- 中文全文对照稿：[[{record["translation"]}]]
{pdf_links}
'''


def module_canvas(module: str, concepts: list[tuple[str, str]]) -> dict[str, Any]:
    extra_papers = [PAPER_BY_CONCEPT[title] for title, _ in concepts if title in PAPER_BY_CONCEPT]
    total_nodes = 1 + len(concepts) + len(extra_papers)
    rows = (total_nodes + 2) // 3
    nodes: list[dict[str, Any]] = [group_node(module[3:], 0, 0, 1160, 100 + rows * 220)]
    overview_path = f"{SUBJECT}/{module}/模块总览.md"
    overview = file_node(overview_path, 40, 50, color="4")
    nodes.append(overview)
    edges: list[dict[str, Any]] = []
    concept_nodes: dict[str, dict[str, Any]] = {}
    for index, (title, _) in enumerate(concepts, start=1):
        row, column = divmod(index, 3)
        node = file_node(f"{SUBJECT}/{module}/{title}.md", 40 + column * 360, 50 + row * 220)
        nodes.append(node)
        concept_nodes[title] = node
        edges.append(edge(overview["id"], node["id"], "组成"))
    start = 1 + len(concepts)
    for offset, paper in enumerate(extra_papers):
        index = start + offset
        row, column = divmod(index, 3)
        node = file_node(f"{SUBJECT}/90_论文证据/{paper}.md", 40 + column * 360, 50 + row * 220, color="5")
        nodes.append(node)
        concept = next(title for title, mapped in PAPER_BY_CONCEPT.items() if mapped == paper)
        edges.append(edge(concept_nodes[concept]["id"], node["id"], "证据支持"))
    return {"nodes": nodes, "edges": edges}


def subject_canvas() -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    module_nodes: list[dict[str, Any]] = []
    for index, module in enumerate(KNOWLEDGE_MODULES):
        row, column = divmod(index, 2)
        x, y = column * 420, row * 280
        nodes.append(group_node(module[3:], x, y, 380, 240))
        node = file_node(f"{SUBJECT}/{module}/模块.canvas", x + 30, y + 50, color=str((index % 6) + 1))
        nodes.append(node)
        module_nodes.append(node)
    labels = ["前置于", "前置于", "组成", "用于", "用于"]
    edges = [edge(module_nodes[i]["id"], module_nodes[i + 1]["id"], labels[i]) for i in range(5)]
    return {"nodes": nodes, "edges": edges}


def bootstrap_vault(vault: Path) -> dict[str, int]:
    vault = Path(vault)
    created = 0
    skipped = 0

    def write(relative: str, text: str) -> None:
        nonlocal created, skipped
        if write_if_missing(vault / relative, text):
            created += 1
        else:
            skipped += 1

    usage = f'''# 使用说明

从 [[00_首页/个人知识网络.canvas]] 开始浏览。

- Canvas 负责导航，Markdown 笔记负责正文。
- `99_自动导入` 是 PaperLab 生成副本，不要人工编辑。
- 学习状态使用：未学、学习中、已理解、待复习。
- 关系类型使用：属于、前置于、组成、用于、对比、证据支持。
'''
    template = '''---
type: concept
status: 未学
module: ""
---

# 概念名称

## 一句话理解

## 知识网络关系

## 学习检查

- [ ] 能用自己的话解释这个概念
- [ ] 能说明它与前置知识的关系
- [ ] 能完成一个最小例子
'''
    write("00_首页/使用说明.md", usage)
    write("90_模板/概念模板.md", template)

    subject_links = "\n".join(f"- [[{SUBJECT}/{module}/模块总览]]" for module in KNOWLEDGE_MODULES)
    write(f"{SUBJECT}/学科总览.md", f"# 深度学习与卷积神经网络\n\n{subject_links}\n")

    for module, concepts in KNOWLEDGE_MODULES.items():
        write(f"{SUBJECT}/{module}/模块总览.md", module_markdown(module, concepts))
        for title, summary in concepts:
            write(f"{SUBJECT}/{module}/{title}.md", concept_markdown(module, title, summary))

    for title, record in PAPER_WRAPPERS.items():
        write(f"{SUBJECT}/90_论文证据/{title}.md", paper_markdown(title, record))

    home_canvas = {
        "nodes": [
            group_node("个人知识网络", 0, 0, 760, 320),
            file_node(f"{SUBJECT}/00_总览.canvas", 40, 60, 680, 220, color="5"),
        ],
        "edges": [],
    }
    write("00_首页/个人知识网络.canvas", json_text(home_canvas))
    write(f"{SUBJECT}/00_总览.canvas", json_text(subject_canvas()))
    for module, concepts in KNOWLEDGE_MODULES.items():
        write(f"{SUBJECT}/{module}/模块.canvas", json_text(module_canvas(module, concepts)))

    return {"created": created, "skipped": skipped, "vault": str(vault)}


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
            source_hash = file_sha256(source)
            if destination.exists() and file_sha256(destination) == source_hash:
                unchanged += 1
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
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "bootstrap":
        result = bootstrap_vault(args.vault)
    else:
        result = sync_artifacts(args.project, args.pdf_dir, args.vault)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
