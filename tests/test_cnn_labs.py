from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / ".paperlab" / "cnn_labs.py"


def load_labs():
    assert MODULE_PATH.exists(), "cnn_labs.py is missing"
    spec = importlib.util.spec_from_file_location("cnn_labs", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_all_lab_smoke_paths_return_finite_interpretable_results():
    module = load_labs()
    results = {
        "autograd": module.run_autograd(),
        "activations": module.run_activations(),
        "lenet": module.run_lenet(),
        "vgg-ablation": module.run_vgg_ablation(),
    }

    assert results["autograd"]["input_shape"] == [4, 2]
    assert results["autograd"]["loss_after"] < results["autograd"]["loss_before"]
    assert results["activations"]["inputs"] == [-5.0, -1.0, 0.0, 1.0, 5.0]
    assert results["lenet"]["logits_shape"] == [8, 10]
    assert results["vgg-ablation"]["deep_parameters"] > results["vgg-ablation"]["shallow_parameters"]

    def numbers(value):
        if isinstance(value, dict):
            for item in value.values():
                yield from numbers(item)
        elif isinstance(value, list):
            for item in value:
                yield from numbers(item)
        elif isinstance(value, float):
            yield value

    assert all(math.isfinite(value) for result in results.values() for value in numbers(result))
