# Obsidian 个人知识网络设计

日期：2026-07-15
状态：已获用户口头批准，等待书面规格复核

## 目标

在 Windows 桌面建立一个可点击、可折叠、可逐层展开的 Obsidian 个人知识网络。第一期只建设“深度学习与卷积神经网络”，同时保留以后增加其他学科的编号规则。

用户应能从总览进入学科、模块、概念和论文证据，并在概念笔记中继续学习。现有 PaperLab 和 Zotero 文件不得被移动、覆盖或删除。

## 非目标

- 第一期不建设物理化学、编程等其他学科的空目录或空节点。
- 不开发自定义 Obsidian 插件。
- 不同时安装多套知识图谱插件。
- 不修改 Zotero 数据库、Zotero storage 或原始 PDF。
- 不把 Canvas 当作知识正文的唯一存储位置。

## 总体架构

采用“原生内容层 + 单插件交互层”：

```text
个人知识网络 Canvas
        ↓
深度学习与 CNN 学科 Canvas
        ↓
模块 Canvas
        ↓
概念 Markdown 笔记
        ↓
公式、代码、图表、论文和证据
```

Markdown 概念笔记是知识内容的唯一事实来源。Canvas 只负责布局、导航和关系展示，不重复保存长篇正文。关闭第三方插件后，笔记、内部链接、原生 Canvas 和局部关系图仍应可用。

## 知识层级

| 层级 | 内容 | 示例 |
|---|---|---|
| L0 | 个人知识网络 | 所有学科入口 |
| L1 | 学科 | 深度学习与 CNN |
| L2 | 模块 | 数学基础、神经网络基础、CNN、训练与评估 |
| L3 | 概念 | 卷积、感受野、池化、反向传播 |
| L4 | 证据与材料 | 公式、代码、图表、论文、PDF |

概念笔记只能使用以下六类关系，避免关系类型无限扩张：

- 属于
- 前置于
- 组成
- 用于
- 对比
- 证据支持

笔记类型限定为：概念、方法、模型、任务、论文、工具。学习状态限定为：未学、学习中、已理解、待复习。

## Obsidian 组件

第一期使用 Obsidian 原生 Canvas、内部链接、属性、模板、反向链接和关系图，只安装一个社区插件 Advanced Canvas。

Advanced Canvas 负责组的折叠与展开，并增强 Canvas 与关系图、反向链接之间的联动。若插件不可用，原生功能仍构成可用的降级路径。

## 用户交互

1. 打开 `个人知识网络.canvas`。
2. 展开“深度学习与 CNN”。
3. 进入学科 Canvas，再展开 CNN 等模块。
4. 点击概念节点，打开对应 Markdown 笔记。
5. 在局部关系图中使用 1 至 3 层深度查看相关概念。
6. 点击论文或证据节点，打开论文笔记或 Vault 内的 PDF 副本。

## Vault 位置与目录

Vault 固定为：

`E:\HuaweiMoveData\Users\XuJiasheng\Desktop\个人知识网络`

第一期目录：

```text
个人知识网络/
├─ 00_首页/
│  ├─ 个人知识网络.canvas
│  └─ 使用说明.md
├─ 10_深度学习与CNN/
│  ├─ 00_总览.canvas
│  ├─ 01_数学与计算基础/
│  ├─ 02_神经网络基础/
│  ├─ 03_卷积神经网络/
│  ├─ 04_其他网络架构/
│  ├─ 05_训练与评估/
│  ├─ 06_应用与前沿/
│  └─ 90_论文证据/
├─ 90_模板/
└─ 99_自动导入/
```

未来学科使用 `20_`、`30_` 等编号，但在真正开始对应学科前不创建目录。

## PaperLab 接入

现有资料中心保持不变：

`E:\HuaweiMoveData\Users\XuJiasheng\Desktop\深度学习CNN研究资料`

PaperLab 继续作为论文产物的唯一事实来源。Obsidian 通过单向导入获得需要展示的最终 PDF、精读稿和证据卡：

```text
PaperLab 产物 → 筛选可用材料 → 99_自动导入 → 概念笔记和 Canvas 链接
```

`99_自动导入` 中的文件视为生成副本，不在 Obsidian 中人工编辑。人工知识笔记与自动导入区分开，后续同步只能更新自动导入文件和明确标记的自动索引区块，不得覆盖人工正文或 Canvas 布局。

第一期需要接入当前四篇论文的精读材料和八个最终 PDF。源文件继续留在 PaperLab/Zotero 工作流原位置。

## 更新规则

- 新论文加入 PaperLab 后，单向刷新 `99_自动导入` 和论文索引。
- 同名概念优先通过别名指向现有笔记，不自动合并或删除。
- 人工修改的概念笔记、关系和 Canvas 坐标不参与自动覆盖。
- 自动导入必须可重复执行，相同输入不得制造重复副本。

## 错误处理

- 源文件暂时缺失：保留已有副本并标记“待同步”，不得删除。
- 导入中断：保留上一次完整结果，不留下半写入文件。
- Advanced Canvas 不可用：回退到原生 Canvas、内部链接和关系图。
- 链接失效：保留节点并标记来源缺失，等待人工确认。
- 发现概念重名：使用别名或人工合并，不执行破坏性自动合并。

## 验收标准

- Obsidian 能打开指定 Vault。
- 首页 Canvas、学科 Canvas 和模块 Canvas 正常显示。
- L0 至 L4 的点击路径至少完整走通一次。
- Advanced Canvas 的分组折叠和展开正常。
- 局部关系图可按 1 至 3 层深度查看关联。
- 当前四篇论文精读材料和八个最终 PDF 均可从知识网络到达。
- 禁用 Advanced Canvas 后，核心导航和阅读仍可使用。
- 重复执行导入不会产生重复文件。
- PaperLab、Zotero 和原始 PDF 未被修改、移动或删除。

## 实施边界

实施阶段只需完成：安装 Obsidian、创建上述 Vault、启用必要原生功能、安装 Advanced Canvas、生成第一期知识节点、单向导入现有论文材料并执行验收。任何额外插件、自动分类算法、跨设备同步和其他学科内容均不属于第一期。

## 参考

- [Obsidian Canvas](https://obsidian.md/help/plugins/canvas)
- [Obsidian Graph view](https://obsidian.md/help/plugins/graph)
- [Obsidian Internal links](https://obsidian.md/help/links)
- [Obsidian URI](https://help.obsidian.md/Extending%2BObsidian/Obsidian%2BURI)
- [Advanced Canvas](https://github.com/Developer-Mike/obsidian-advanced-canvas)
