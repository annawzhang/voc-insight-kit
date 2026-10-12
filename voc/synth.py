"""生成虚构的社媒评论快照（含点赞、IP、重复转发和无关灌水）。

每条评论带算法看不到的真实议题标签，用来离线评估编码准确率。
"""

import math
import random
from dataclasses import dataclass, field

PROVINCES = ["广东", "浙江", "江苏", "上海", "北京", "四川", "山东", "湖北", "河南", "福建", "湖南", "陕西"]

FRAGMENTS = {
    "overlap": {
        "neg": ["有 A8 和 M7 了，A9 真的没必要", "A9 和 M7 定位重叠，自己人内耗", "A8 还没卖明白又出 A9，多余"],
        "neu": ["A9 和 A8 到底差在哪", "A9 的定位是不是在 A8 和 M7 中间"],
        "pos": ["A9 补上了 A8 和 M7 中间的空档，支持"],
    },
    "design": {
        "neg": ["溜背造型不适合三排家用", "这外观有点丑，像缩小版 MPV", "大型 SUV 还是要方正，溜背劝退"],
        "neu": ["实车颜色看着怎么样", "外观要看实车"],
        "pos": ["这个造型挺好看的，年轻", "溜背好看，喜欢这个设计"],
    },
    "sales": {
        "neg": ["销量估计是 A8 的零头", "这个价位大概率要扑", "感觉卖不动"],
        "neu": ["首月能卖多少", "销量看定价吧"],
        "pos": ["这款能成爆款", "9 系不会差的，销量没问题"],
    },
    "spec": {
        "neg": ["没有新芯片的话就失望了", "电池没升级就劝退"],
        "neu": ["电池是不是大一号", "智驾芯片上不上新的", "底盘配置有消息吗"],
        "pos": ["新芯片加大电池，期待续航", "一体连屏加线控底盘，期待"],
    },
    "intent": {
        "neg": ["已经不考虑了", "放弃了，不买", "观望太久劝退了"],
        "neu": ["观望中，看门店能不能先试驾", "再看看，等试驾"],
        "pos": ["等 A9，搞快点", "期待，什么时候能试驾"],
    },
    "trust": {
        "neg": ["老车主又被背刺", "首发就买的人亏麻了，降价太快", "保值率堪忧"],
        "neu": ["老车主有没有置换补贴"],
        "pos": ["老车主有置换补贴就支持"],
    },
}
PRICE_NEG = ["{p} 万起？劝退", "超过 {p} 万就别费事生产了", "{p} 万太贵了，不买"]
PRICE_POS = ["{p} 万以内可以考虑", "{p} 万左右挺值", "{p} 万的话真香"]
PRICE_RUMORS = [34.98, 36.98, 37.98, 38.98, 39.98, 41.98, 42.98, 44.98, 46.98]
NOISE = ["沙发", "哈哈哈哈", "求博主链接", "路过", "已关注", "第一"]
LOCKED = ["已经订了别的车", "上个月提了竞品"]
OPENERS = ["", "", "", "说实话", "个人觉得", "感觉", "讲真", "我觉得", "坦白说", "emmm", "看完了"]
CLOSERS = ["", "", "", "吧", "啊", "🤔", "，坐等", "，蹲一个", "😂", "，懂的都懂", "，纯个人看法", "，你们觉得呢"]


@dataclass
class Comment:
    id: int
    text: str
    likes: int
    ip: str
    topics: set[str] = field(repr=False)
    stance: str = field(repr=False)
    price: float | None = field(default=None, repr=False)


def _likes(rng: random.Random, weight: float) -> int:
    return int(math.exp(rng.gauss(0.8 + weight, 1.3)))


def generate(n: int = 900, seed: int = 8, dup_rate: float = 0.06, noise_rate: float = 0.08) -> list[Comment]:
    rng = random.Random(seed)
    out: list[Comment] = []
    stance_bias = {"price": 0.55, "overlap": 0.6, "design": 0.45, "sales": 0.6, "spec": 0.15, "intent": 0.3, "trust": 0.6}
    while len(out) < n:
        cid = len(out) + 1
        roll = rng.random()
        if roll < noise_rate:
            out.append(Comment(cid, rng.choice(NOISE), _likes(rng, -1.2), rng.choice(PROVINCES), set(), "neu"))
            continue
        if roll < noise_rate + dup_rate and out:
            src = rng.choice([c for c in out if c.topics] or out)
            text = src.text + rng.choice(["", "！", "。", " +1", "…"])
            out.append(Comment(cid, text, _likes(rng, -1.0), rng.choice(PROVINCES), set(src.topics), src.stance, src.price))
            continue

        primary = rng.choices(list(stance_bias), weights=[26, 18, 16, 10, 12, 12, 6])[0]
        topics, parts, price = {primary}, [], None
        if primary == "price":
            accept = rng.gauss(40.5, 2.0)
            price = rng.choice(PRICE_RUMORS)
            negative = price > accept
            parts.append(rng.choice(PRICE_NEG if negative else PRICE_POS).format(p=f"{price:g}"))
            stance = "neg" if negative else "pos"
        else:
            r = rng.random()
            stance = "neg" if r < stance_bias[primary] else ("pos" if r < stance_bias[primary] + 0.2 else "neu")
            parts.append(rng.choice(FRAGMENTS[primary][stance]))
            if primary == "intent" and stance == "neg" and rng.random() < 0.3:
                parts[-1] = rng.choice(LOCKED)
        if rng.random() < 0.3:
            extra = rng.choice([k for k in FRAGMENTS if k != primary])
            topics.add(extra)
            parts.append(rng.choice(FRAGMENTS[extra][stance if stance in FRAGMENTS[extra] else "neu"]))
        hot = 0.8 if stance == "neg" else 0.4
        opener = rng.choice(OPENERS)
        text = (opener + "，" if opener else "") + "，".join(parts) + rng.choice(CLOSERS)
        out.append(Comment(cid, text, _likes(rng, hot), rng.choice(PROVINCES), topics, stance, price))
    return out
