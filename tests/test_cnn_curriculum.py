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
