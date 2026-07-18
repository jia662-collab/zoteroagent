from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".agents" / "skills" / "paper-research" / "SKILL.md"


def test_repository_skill_declares_natural_language_workflow_and_limits():
    text = SKILL.read_text(encoding="utf-8")
    assert text.startswith("---\nname: paper-research\ndescription:")
    assert "开始研究" in text
    assert "继续" in text
    assert "恢复项目" in text
    assert "每轮最多 15 篇" in text
    assert "read --outline" in text
    assert "不设置固定页数或字符上限" in text
    assert "最多 8 页" not in text
    assert "20,000" not in text
    assert "最多 5 张证据卡" in text
    assert "当前项目：<project_id>；下一步：<action>" in text
    assert "不得读取完整 `library.bib`" in text
    assert len(text.splitlines()) < 300


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


def test_skill_protects_human_notes_and_source_evidence():
    text = SKILL.read_text(encoding="utf-8")
    method = (SKILL.parent / "references" / "deep-reading.md").read_text(encoding="utf-8")
    combined = text + method
    assert "<!-- PAPERLAB:AUTO:START -->" in text
    assert "<!-- PAPERLAB:AUTO:END -->" in text
    assert "## 人工确认" in text
    assert "不得覆盖" in text
    assert "作者明确陈述" in combined
    assert "数据直接支持" in combined
    assert "合理推断" in combined
    assert "Codex 的解释" in combined
    assert "无法确认" in combined


def test_skill_defines_illustrated_narrative_notes_and_lean_handoffs():
    text = SKILL.read_text(encoding="utf-8")
    for requirement in [
        "候选：<n>｜已在 Zotero：<n>｜有 PDF：<n>｜可精读：<n>｜待导入：<n>",
        "资源管理器",
        "inspect --page <n> --label <label>",
        "visually inspect only the final crop",
        "translations/<citation_key>.md",
        "papers/<citation_key>.md",
        "机器辅助翻译，原文为准",
        "output/pdf/<project_id>/",
        "只传本次新增",
        "阶段性综合",
    ]:
        assert requirement in text
    assert "检测到 References 后停止" in text
    assert "render" in text


def test_skill_has_desktop_metadata():
    metadata = (SKILL.parent / "agents" / "openai.yaml").read_text(encoding="utf-8")
    assert 'display_name: "Paper Research"' in metadata
    assert 'short_description: "用自然语言管理可恢复的 Zotero 论文研究流程"' in metadata
    assert "default_prompt:" in metadata


def test_agent_rules_force_resume_from_files_not_chat_history():
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert ".agents/skills/paper-research/SKILL.md" in text
    assert "PROJECT.md" in text
    assert "STATUS.md" in text
    assert "不得依赖聊天历史作为唯一状态来源" in text
    assert "不直接修改 `zotero.sqlite`" in text


def test_readme_starts_with_research_actions_not_commands():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    first_section = text.split("## 技术维护", 1)[0]
    assert "你只需要这样说" in first_section
    assert "开始研究" in first_section
    assert "把第 2、5、7 篇导入 Zotero" in first_section
    assert "python .paperlab" not in first_section
    assert "config/research_profile.yaml" not in text


def test_readme_contains_concrete_end_to_end_steps():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    for instruction in [
        "右键“我的文库”",
        "Keep updated",
        "文件 > 导入",
        "zotero_import.ris",
        "我已经导入并添加 PDF，继续",
        "research/projects/<项目编号>/search.md",
        "从我的 Zotero 中筛选",
        "pending_push",
    ]:
        assert instruction in text
    assert "按章节完整读取" in text
    assert "中文全文对照稿" in text
    assert "精读学习稿" in text
    assert "每篇论文分配一个子代理" in text
    assert "每次最多读取 8 页" not in text


def test_old_operator_facing_structure_is_removed():
    for relative in ["config", "prompts", "scripts", "tables", "reports", "notes", "papers", "synthesis", "flashcards", "inbox"]:
        assert not (ROOT / relative).exists(), relative
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "PyYAML" not in requirements
    assert "rapidfuzz" not in requirements


def test_skill_requires_two_distinct_reading_pdfs_and_progressive_narrative():
    text = SKILL.read_text(encoding="utf-8")
    method = (SKILL.parent / "references" / "deep-reading.md").read_text(encoding="utf-8")

    for requirement in [
        "中文全文对照版",
        "精读学习版",
        "translations/<citation_key>.md",
        "按原论文的章节与页码对齐",
        "沿作者的论证顺序",
        "不得用“问题、方法、结果、贡献”重新横向切块",
    ]:
        assert requirement in text + method

    assert "关键证据一句话" not in method
    assert "上一步留下的问题" in method
    assert "这一节回答了什么" in method
    assert "下一节为什么出现" in method
    assert "原文 PDF 页码" in method


def test_skill_defines_one_paper_per_subagent_with_coordinator_owned_state():
    text = SKILL.read_text(encoding="utf-8")
    method = (SKILL.parent / "references" / "deep-reading.md").read_text(encoding="utf-8")
    combined = text + method

    for requirement in [
        "每篇论文一个子代理",
        "协调代理",
        "分波次",
        "一个论文失败不得取消其他论文",
        "只有协调代理可以更新",
        "PROJECT.md",
        "STATUS.md",
        "state/<project_id>.json",
        "synthesis.md",
    ]:
        assert requirement in combined
