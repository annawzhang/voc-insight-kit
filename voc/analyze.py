"""清洗、议题编码、情感、点赞加权、价格锚点与人群划分。"""

import re
import tomllib
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUNCT = re.compile(r"(?:\s*\+1|[\s，。！？、…!?,.~])+$")
PRICE = re.compile(r"(\d{2}(?:\.\d{1,2})?)\s*万")


def load_codebook(path: Path = ROOT / "config" / "codebook.toml") -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


def normalize(text: str) -> str:
    return PUNCT.sub("", text.strip()).replace(" ", "")


@dataclass
class Coded:
    id: int
    text: str
    likes: int
    ip: str
    topics: set[str]
    stance: str
    persona: str | None
    price: float | None
    truth: object = field(repr=False, default=None)


def dedupe(comments: list) -> tuple[list, int]:
    """完全相同或只差标点的评论只保留第一条，点赞合并到保留的那条。"""
    kept, index = [], {}
    for c in comments:
        key = normalize(c.text)
        if key in index:
            index[key].likes += c.likes
            continue
        clone = type(c)(**{**c.__dict__})
        index[key] = clone
        kept.append(clone)
    return kept, len(comments) - len(kept)


def code_topics(text: str, cb: dict) -> set[str]:
    hit = set()
    for t in cb["topics"]:
        if any(x in text for x in t.get("exclude", [])):
            continue
        if any(k in text for k in t["keywords"]):
            hit.add(t["key"])
    return hit


def stance_of(text: str, cb: dict) -> str:
    s = cb["stance"]
    score = 0
    for words, sign in ((s["positive"], 1), (s["negative"], -1)):
        for w in words:
            for m in re.finditer(re.escape(w), text):
                window = text[max(0, m.start() - 2):m.start()]
                flipped = any(n in window for n in s["negations"]) and not any(n in w for n in s["negations"])
                score += -sign if flipped else sign
    return "pos" if score > 0 else "neg" if score < 0 else "neu"


def persona_of(text: str, cb: dict) -> str | None:
    for key, p in cb["personas"].items():
        if any(k in text for k in p["keywords"]):
            return key
    return None


def extract_price(text: str) -> float | None:
    values = [float(v) for v in PRICE.findall(text) if 20 <= float(v) <= 80]
    return values[0] if values else None


def code_all(comments: list, cb: dict) -> list[Coded]:
    out = []
    for c in comments:
        topics = code_topics(c.text, cb)
        if not topics:
            continue
        out.append(Coded(c.id, c.text, c.likes, c.ip, topics, stance_of(c.text, cb),
                         persona_of(c.text, cb), extract_price(c.text), truth=c))
    return out


def coding_quality(coded: list[Coded], raw: list, cb: dict) -> dict[str, dict]:
    """用模拟数据的真实议题标签评估编码的精确率与召回率。"""
    by_id = {c.id: c for c in coded}
    out = {}
    for t in cb["topics"]:
        k = t["key"]
        tp = fp = fn = 0
        for c in raw:
            pred = k in by_id[c.id].topics if c.id in by_id else False
            truth = k in c.topics
            tp += pred and truth
            fp += pred and not truth
            fn += truth and not pred
        out[k] = {"precision": tp / max(1, tp + fp), "recall": tp / max(1, tp + fn), "support": tp + fn}
    return out


@dataclass
class TopicSummary:
    key: str
    name: str
    question: str
    count: int
    share: float
    like_share: float
    neg_rate: float
    like_neg_rate: float
    pos_rate: float
    quotes: list[Coded]


def summarize(coded: list[Coded], cb: dict, quotes: int = 3) -> list[TopicSummary]:
    total = len(coded)
    total_likes = sum(c.likes for c in coded) or 1
    out = []
    for t in cb["topics"]:
        rows = [c for c in coded if t["key"] in c.topics]
        if not rows:
            continue
        likes = sum(c.likes for c in rows) or 1
        neg = [c for c in rows if c.stance == "neg"]
        out.append(TopicSummary(
            key=t["key"], name=t["name"], question=t["question"], count=len(rows),
            share=len(rows) / total, like_share=likes / total_likes,
            neg_rate=len(neg) / len(rows), like_neg_rate=sum(c.likes for c in neg) / likes,
            pos_rate=sum(c.stance == "pos" for c in rows) / len(rows),
            quotes=sorted(rows, key=lambda c: -c.likes)[:quotes]))
    return sorted(out, key=lambda s: -s.like_share)


def price_curve(coded: list[Coded]) -> list[dict]:
    """每个被提到的价格点上，负面评论占比。"""
    buckets = defaultdict(lambda: [0, 0])
    for c in coded:
        if c.price is None or c.stance == "neu":
            continue
        b = buckets[c.price]
        b[0] += 1
        b[1] += c.stance == "neg"
    return [{"price": p, "n": n, "neg_rate": neg / n} for p, (n, neg) in sorted(buckets.items())]


def price_ceiling(curve: list[dict], min_n: int = 8) -> float | None:
    """负面占比首次过半的价格点，即用户心理关口。"""
    for row in curve:
        if row["n"] >= min_n and row["neg_rate"] > 0.5:
            return row["price"]
    return None


def personas(coded: list[Coded], cb: dict) -> list[tuple[str, int, float]]:
    counts = Counter(c.persona for c in coded if c.persona)
    total = sum(counts.values()) or 1
    return [(cb["personas"][k]["name"], counts[k], counts[k] / total) for k in cb["personas"] if counts[k]]


def co_mention(coded: list[Coded], cb: dict) -> dict[str, float]:
    total = len(coded) or 1
    return {s: sum(s in c.text for c in coded) / total for s in cb["siblings"]}
