"""生成模拟评论快照并输出 docs/index.html、docs/coded_comments.csv。"""

import csv
from pathlib import Path

from voc.analyze import (co_mention, code_all, coding_quality, dedupe, load_codebook, personas,
                         price_ceiling, price_curve, summarize)
from voc.report import render
from voc.scripts import lint_playbook, load_scripts, playbook_for
from voc.synth import generate

ROOT = Path(__file__).resolve().parent
PARAMS = {"n": 900, "seed": 8}


def main() -> None:
    codebook = load_codebook()
    script_cfg = load_scripts()
    raw = generate(PARAMS["n"], PARAMS["seed"])
    kept, dup_n = dedupe(raw)
    coded = code_all(kept, codebook)
    summaries = summarize(coded, codebook)
    curve = price_curve(coded)
    ceiling = price_ceiling(curve)
    issues = lint_playbook(script_cfg)
    if issues:
        for concern, v in issues:
            print(f"话术违规：{concern} 「{v.match}」{v.reason}")

    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "index.html").write_text(render(
        raw_n=len(raw), dup_n=dup_n, noise_n=len(kept) - len(coded), coded=coded, summaries=summaries,
        curve=curve, ceiling=ceiling, persona_items=personas(coded, codebook), co=co_mention(coded, codebook),
        quality=coding_quality(coded, kept, codebook), script_cfg=script_cfg,
        playbook=playbook_for([s.key for s in summaries], script_cfg), playbook_issues=issues,
        codebook=codebook), encoding="utf-8")

    names = {t["key"]: t["name"] for t in codebook["topics"]}
    with open(docs / "coded_comments.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["id", "text", "likes", "ip", "topics", "stance", "persona", "price"])
        for c in sorted(coded, key=lambda c: -c.likes):
            w.writerow([c.id, c.text, c.likes, c.ip, "、".join(names[t] for t in sorted(c.topics)),
                        c.stance, c.persona or "", c.price or ""])

    print(f"评论 {len(raw)} 条 → 去重 {dup_n} → 有效 {len(coded)}")
    print("议题（按点赞占比）：" + "、".join(f"{s.name} {s.like_share:.0%}" for s in summaries))
    print(f"心理价位关口：{ceiling} 万")
    print(f"报告 → {docs / 'index.html'}")


if __name__ == "__main__":
    main()
