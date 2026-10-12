"""话术库加载与禁止话术检查。"""

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STEP_NAMES = ["认同", "重构", "转移", "落地"]


def load_scripts(path: Path = ROOT / "config" / "scripts.toml") -> dict:
    with open(path, "rb") as f:
        cfg = tomllib.load(f)
    for entry in cfg["playbook"]:
        if len(entry["steps"]) != len(STEP_NAMES):
            raise ValueError(f"「{entry['concern']}」需要 {len(STEP_NAMES)} 步，当前 {len(entry['steps'])} 步")
        if entry["model"] not in cfg["models"]:
            raise ValueError(f"未知车型 {entry['model']}")
    return cfg


@dataclass
class Violation:
    match: str
    reason: str


def lint(text: str, cfg: dict) -> list[Violation]:
    out = []
    for rule in cfg["forbidden"]:
        for m in re.finditer(rule["pattern"], text):
            out.append(Violation(m.group(0), rule["reason"]))
    return out


def lint_playbook(cfg: dict) -> list[tuple[str, Violation]]:
    return [(e["concern"], v) for e in cfg["playbook"] for s in e["steps"] for v in lint(s, cfg)]


def playbook_for(topics: list[str], cfg: dict) -> list[dict]:
    """按 VOC 议题热度排序话术，热门顾虑排在前面。"""
    rank = {t: i for i, t in enumerate(topics)}
    return sorted(cfg["playbook"], key=lambda e: rank.get(e["topic"], len(rank)))
