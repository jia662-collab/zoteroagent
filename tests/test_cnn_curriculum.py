from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / ".paperlab" / "cnn_curriculum.py"


def load_curriculum():
    assert MODULE_PATH.exists(), "cnn_curriculum.py is missing"
    spec = importlib.util.spec_from_file_location("cnn_curriculum", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_curriculum_has_45_substantive_lessons_and_four_labs():
    module = load_curriculum()
    assert len(module.LESSONS) == 45
    assert len(module.LABS) == 4
    assert module.validate_curriculum() == []

    banned = ("补充一个", "说明这个概念", "记录最容易", "以后补充", "TODO", "TBD")
    for title, lesson in module.LESSONS.items():
        combined = "\n".join(
            [
                lesson.intuition,
                lesson.mechanism,
                lesson.worked_example,
                lesson.work_context,
                lesson.practice,
                lesson.evidence,
                lesson.pitfalls,
            ]
        )
        assert not any(phrase in combined for phrase in banned), title
        assert re.search(r"\d|×|→|\$|shape|形状", combined), title
        assert len(combined) >= 380, title
        if title in module.CORE_LESSONS:
            assert lesson.lab, title


def test_paper_evidence_is_anchored_and_nonpaper_evidence_is_explicit():
    module = load_curriculum()
    for title, lesson in module.LESSONS.items():
        if "论文证据" in lesson.evidence:
            assert re.search(r"第\s*\d+.*页|图\s*\d+|表\s*\d+", lesson.evidence), title
            assert "[[10_深度学习与CNN/07_论文与证据/" in lesson.evidence, title
        else:
            assert "教材性知识（当前四篇论文未直接覆盖）" in lesson.evidence, title


def test_formulas_use_obsidian_mathjax_delimiters():
    module = load_curriculum()
    assert len(module.FORMULAS) >= 20

    for title, formula in module.FORMULAS.items():
        assert title in module.LESSONS
        assert formula.startswith("$$\n") and formula.endswith("\n$$"), title
        assert "\\(" not in formula and "\\)" not in formula, title
        assert "\\[" not in formula and "\\]" not in formula, title


def test_paper_roadmap_is_tiered_verified_and_mapped_to_lessons():
    module = load_curriculum()
    papers = module.PAPER_ROADMAP
    assert len(papers) == 21
    assert len({paper.title for paper in papers}) == len(papers)
    assert {paper.tier for paper in papers} == {"导航综述", "必读主线", "任务分支", "扩展阅读"}
    assert sum(paper.tier == "必读主线" for paper in papers) == 12
    assert sum(paper.tier == "任务分支" for paper in papers) == 5
    assert sum(paper.tier == "扩展阅读" for paper in papers) == 3

    for paper in papers:
        assert paper.url.startswith("https://"), paper.title
        assert paper.year.isdigit(), paper.title
        assert paper.role and paper.authors, paper.title
        assert paper.status in {"精读完成", "待导入与精读"}, paper.title
        assert all(title in module.LESSONS for title in paper.concepts), paper.title
        if paper.status == "精读完成":
            assert paper.wrapper.startswith("[[10_深度学习与CNN/07_论文与证据/"), paper.title
