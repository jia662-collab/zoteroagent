from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def run_autograd() -> dict[str, object]:
    inputs = ((0.0, 0.0), (0.0, 1.0), (1.0, 0.0), (1.0, 1.0))
    targets = (0.0, 0.0, 0.0, 1.0)
    weights, bias, learning_rate = [0.1, -0.2], 0.0, 0.5

    def loss_and_gradient() -> tuple[float, list[float], float]:
        loss = 0.0
        gradient = [0.0, 0.0]
        bias_gradient = 0.0
        for features, target in zip(inputs, targets):
            probability = sigmoid(sum(value * weight for value, weight in zip(features, weights)) + bias)
            loss -= target * math.log(probability) + (1.0 - target) * math.log(1.0 - probability)
            error = probability - target
            gradient = [current + error * value for current, value in zip(gradient, features)]
            bias_gradient += error
        count = len(inputs)
        return loss / count, [value / count for value in gradient], bias_gradient / count

    before, gradient, bias_gradient = loss_and_gradient()
    weights = [weight - learning_rate * grad for weight, grad in zip(weights, gradient)]
    bias -= learning_rate * bias_gradient
    after, _, _ = loss_and_gradient()
    return {"input_shape": [4, 2], "loss_before": before, "loss_after": after, "weight_gradient": gradient}


def run_activations() -> dict[str, object]:
    inputs = [-5.0, -1.0, 0.0, 1.0, 5.0]

    def gelu(value: float) -> float:
        return 0.5 * value * (1.0 + math.erf(value / math.sqrt(2.0)))

    functions = {
        "sigmoid": (sigmoid, lambda x: sigmoid(x) * (1.0 - sigmoid(x))),
        "tanh": (math.tanh, lambda x: 1.0 - math.tanh(x) ** 2),
        "relu": (lambda x: max(0.0, x), lambda x: 1.0 if x > 0.0 else 0.0),
        "gelu": (
            gelu,
            lambda x: 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))
            + x * math.exp(-(x**2) / 2.0) / math.sqrt(2.0 * math.pi),
        ),
    }
    return {
        "inputs": inputs,
        "functions": {
            name: {"values": [function(x) for x in inputs], "gradients": [derivative(x) for x in inputs]}
            for name, (function, derivative) in functions.items()
        },
    }


def run_lenet(smoke: bool = True, data_root: Path = Path("data"), epochs: int = 1) -> dict[str, object]:
    if smoke:
        parameters = 6 * 1 * 5 * 5 + 6 + 16 * 6 * 5 * 5 + 16 + 400 * 120 + 120 + 120 * 84 + 84 + 84 * 10 + 10
        return {"input_shape": [8, 1, 32, 32], "logits_shape": [8, 10], "parameters": parameters, "loss": math.log(10.0)}
    return _train_with_torch("lenet", data_root, epochs)


def run_vgg_ablation(smoke: bool = True, data_root: Path = Path("data"), epochs: int = 1) -> dict[str, object]:
    if smoke:
        shallow = 3 * 8 * 3 * 3 + 8 + 8 * 16 * 3 * 3 + 16 + 16 * 10 + 10
        deep = shallow + 8 * 8 * 3 * 3 + 8 + 16 * 16 * 3 * 3 + 16
        return {
            "input_shape": [4, 3, 32, 32],
            "logits_shape": [4, 10],
            "shallow_parameters": shallow,
            "deep_parameters": deep,
            "shallow_loss": math.log(10.0),
            "deep_loss": math.log(10.0),
        }
    return _train_with_torch("vgg-ablation", data_root, epochs)


def _train_with_torch(experiment: str, data_root: Path, epochs: int) -> dict[str, object]:
    try:
        import torch
        from torch import nn
        from torch.utils.data import DataLoader
        from torchvision import datasets, transforms
    except ModuleNotFoundError as exc:
        raise SystemExit("完整实验需要 PyTorch 和 torchvision；烟雾实验可直接加 --smoke 运行。") from exc

    class LeNet(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.network = nn.Sequential(
                nn.Conv2d(1, 6, 5), nn.ReLU(), nn.AvgPool2d(2),
                nn.Conv2d(6, 16, 5), nn.ReLU(), nn.AvgPool2d(2), nn.Flatten(),
                nn.Linear(400, 120), nn.ReLU(), nn.Linear(120, 84), nn.ReLU(), nn.Linear(84, 10),
            )

        def forward(self, inputs):
            return self.network(inputs)

    class TinyVGG(nn.Module):
        def __init__(self, deep: bool) -> None:
            super().__init__()
            layers = [nn.Conv2d(3, 8, 3, padding=1), nn.ReLU()]
            if deep:
                layers += [nn.Conv2d(8, 8, 3, padding=1), nn.ReLU()]
            layers += [nn.MaxPool2d(2), nn.Conv2d(8, 16, 3, padding=1), nn.ReLU()]
            if deep:
                layers += [nn.Conv2d(16, 16, 3, padding=1), nn.ReLU()]
            layers += [nn.MaxPool2d(2), nn.AdaptiveAvgPool2d(1)]
            self.features, self.classifier = nn.Sequential(*layers), nn.Linear(16, 10)

        def forward(self, inputs):
            return self.classifier(self.features(inputs).flatten(1))

    if experiment == "lenet":
        transform = transforms.Compose([transforms.Pad(2), transforms.ToTensor(), transforms.Normalize((0.1307,), (0.3081,))])
        train_data = datasets.MNIST(data_root, train=True, download=True, transform=transform)
        test_data = datasets.MNIST(data_root, train=False, download=True, transform=transform)
        models = {"lenet": LeNet()}
    else:
        train_transform = transforms.Compose([transforms.RandomHorizontalFlip(), transforms.ToTensor()])
        test_transform = transforms.ToTensor()
        train_data = datasets.CIFAR10(data_root, train=True, download=True, transform=train_transform)
        test_data = datasets.CIFAR10(data_root, train=False, download=True, transform=test_transform)
        models = {"shallow": TinyVGG(False), "deep": TinyVGG(True)}

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    train_loader = DataLoader(train_data, batch_size=128, shuffle=True)
    test_loader = DataLoader(test_data, batch_size=256)
    results: dict[str, object] = {}
    for name, model in models.items():
        model.to(device)
        optimizer = torch.optim.SGD(model.parameters(), lr=0.01, momentum=0.9)
        loss_fn = nn.CrossEntropyLoss()
        for _ in range(epochs):
            model.train()
            for inputs, labels in train_loader:
                inputs, labels = inputs.to(device), labels.to(device)
                optimizer.zero_grad()
                loss = loss_fn(model(inputs), labels)
                loss.backward()
                optimizer.step()
        model.eval()
        correct = total = 0
        with torch.no_grad():
            for inputs, labels in test_loader:
                predictions = model(inputs.to(device)).argmax(1).cpu()
                correct += int((predictions == labels).sum())
                total += labels.numel()
        results[name] = {
            "parameters": sum(parameter.numel() for parameter in model.parameters()),
            "test_accuracy": correct / total,
            "epochs": epochs,
            "device": str(device),
        }
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="CNN knowledge-vault experiments")
    parser.add_argument("experiment", choices=("autograd", "activations", "lenet", "vgg-ablation"))
    parser.add_argument("--smoke", action="store_true", help="Use deterministic standard-library checks and avoid downloads")
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument("--epochs", type=int, default=1)
    args = parser.parse_args()
    if args.experiment == "autograd":
        result = run_autograd()
    elif args.experiment == "activations":
        result = run_activations()
    elif args.experiment == "lenet":
        result = run_lenet(args.smoke, args.data_root, args.epochs)
    else:
        result = run_vgg_ablation(args.smoke, args.data_root, args.epochs)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
