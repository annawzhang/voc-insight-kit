"""生成单文件 HTML 报告：舆情洞察 + 决策建议 + 话术手册 + 禁止话术检查。"""

import re
from html import escape

from .scripts import STEP_NAMES, lint

CSS = """
:root { --text:#0f172a; --muted:#64748b; --border:#e2e8f0; --accent:#dc2626; --bg:#f8fafc; }
* { box-sizing:border-box; }
body { margin:0; font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif; background:var(--bg); color:var(--text); }
.wrap { max-width:1120px; margin:0 auto; padding:30px 22px 48px; }
h1 { margin:0 0 6px; font-size:1.55rem; } h2 { font-size:1.02rem; margin:30px 0 12px; }
.meta { color:var(--muted); font-size:0.86rem; line-height:1.7; }
.badge { display:inline-block; margin-left:8px; padding:1px 8px; border-radius:999px; background:#fef3c7; color:#92400e; font-size:0.74rem; }
.grid { display:grid; gap:14px; } .g4 { grid-template-columns:repeat(4,1fr); } .g2 { grid-template-columns:1fr 1fr; } .g3 { grid-template-columns:repeat(3,1fr); }
@media (max-width:860px) { .g4,.g2,.g3 { grid-template-columns:1fr; } }
.card { background:#fff; border:1px solid var(--border); border-radius:12px; padding:16px; }
.kpi .label { color:var(--muted); font-size:0.78rem; } .kpi .value { font-size:1.45rem; font-weight:700; margin-top:4px; } .kpi .sub { color:var(--muted); font-size:0.76rem; margin-top:3px; }
.flow { display:flex; flex-wrap:wrap; gap:6px; align-items:center; font-size:0.82rem; margin-top:12px; }
.flow span { background:#fef2f2; color:#991b1b; padding:5px 11px; border-radius:999px; } .flow i { color:var(--muted); font-style:normal; }
table { width:100%; border-collapse:collapse; font-size:0.82rem; }
th, td { text-align:left; padding:7px 8px; border-bottom:1px solid var(--border); vertical-align:top; }
th { color:var(--muted); font-weight:600; } td.num, th.num { text-align:right; font-variant-numeric:tabular-nums; }
.quote { color:#334155; } .likes { color:var(--muted); font-size:0.74rem; margin-left:4px; }
.neg { color:#b91c1c; font-weight:600; }
.muted { color:var(--muted); font-size:0.78rem; line-height:1.6; }
.hbar { display:flex; align-items:center; gap:8px; font-size:0.8rem; margin:6px 0; }
.hbar .name { width:84px; color:#334155; } .hbar .track { flex:1; background:#f1f5f9; border-radius:4px; height:10px; }
.hbar .fill { height:10px; border-radius:4px; background:#f97316; } .hbar .v { width:84px; text-align:right; color:var(--muted); }
.must td:first-child { font-weight:600; white-space:nowrap; } .do { color:#047857; } .dont { color:#b91c1c; }
.script h3 { margin:0; font-size:0.9rem; } .tag { display:inline-block; font-size:0.72rem; padding:1px 7px; border-radius:6px; background:#eef2ff; color:#3730a3; margin-right:6px; }
.script ol { margin:10px 0 0; padding-left:0; list-style:none; font-size:0.82rem; line-height:1.65; }
.script li { display:flex; gap:8px; margin-bottom:6px; } .script li b { flex:none; width:34px; color:#dc2626; font-size:0.76rem; padding-top:1px; }
mark { background:#fee2e2; color:#991b1b; padding:0 2px; border-radius:3px; }
.ok { color:#047857; font-weight:600; } .bad { color:#b91c1c; font-weight:600; }
footer { margin-top:36px; color:var(--muted); font-size:0.78rem; }
"""


def pct(v: float) -> str:
    return f"{v:.0%}"


def topic_rows(summaries) -> str:
    rows = []
    for s in summaries:
        q = s.quotes[0]
        rows.append(
            f"<tr><td><strong>{s.name}</strong><div class='muted'>{escape(s.question)}</div></td>"
            f"<td class='num'>{s.count}<div class='muted'>{pct(s.share)}</div></td>"
            f"<td class='num'>{pct(s.like_share)}</td>"
            f"<td class='num'>{pct(s.neg_rate)}<div class='muted'>点赞加权 <span class='neg'>{pct(s.like_neg_rate)}</span></div></td>"
            f"<td class='quote'>「{escape(q.text)}」<span class='likes'>{q.likes} 赞 · {q.ip}</span></td></tr>")
    return "".join(rows)


def price_svg(curve: list[dict], ceiling: float | None) -> str:
    w, h, pad = 520, 220, 34
    step = (w - pad * 2) / len(curve)
    svg = [f'<svg viewBox="0 0 {w} {h}" width="100%">',
           f'<line x1="{pad}" y1="{pad + (h - pad * 2) / 2}" x2="{w - pad}" y2="{pad + (h - pad * 2) / 2}" stroke="#94a3b8" stroke-dasharray="4 4"/>',
           f'<text x="{pad + 2}" y="{pad + (h - pad * 2) / 2 - 5}" font-size="10" fill="#64748b">负面 50%</text>']
    for i, r in enumerate(curve):
        bh = r["neg_rate"] * (h - pad * 2)
        x = pad + i * step + step * 0.18
        color = "#dc2626" if ceiling is not None and r["price"] >= ceiling else "#fca5a5"
        svg.append(f'<rect x="{x:.1f}" y="{h - pad - bh:.1f}" width="{step * 0.64:.1f}" height="{bh:.1f}" fill="{color}" rx="3"/>')
        svg.append(f'<text x="{x + step * 0.32:.1f}" y="{h - pad - bh - 5:.1f}" font-size="10" text-anchor="middle" fill="#0f172a">{pct(r["neg_rate"])}</text>')
        svg.append(f'<text x="{x + step * 0.32:.1f}" y="{h - pad + 14}" font-size="10" text-anchor="middle" fill="#64748b">{r["price"]:g}</text>')
        svg.append(f'<text x="{x + step * 0.32:.1f}" y="{h - pad + 26}" font-size="9" text-anchor="middle" fill="#94a3b8">n={r["n"]}</text>')
    svg.append(f'<text x="{pad}" y="14" font-size="11" fill="#475569">各价格点评论中的负面占比（万元）</text>')
    return "".join(svg) + "</svg>"


def hbars(items: list[tuple[str, int, float]]) -> str:
    return "".join(
        f"<div class='hbar'><span class='name'>{escape(n)}</span><span class='track'><span class='fill' style='display:block;width:{v * 100:.0f}%'></span></span>"
        f"<span class='v'>{c} 人 · {pct(v)}</span></div>" for n, c, v in items)


def decisions(price_ceiling, curve, co, summaries) -> str:
    below = next((r for r in reversed(curve) if price_ceiling and r["price"] < price_ceiling), None)
    by_key = {s.key: s for s in summaries}
    sib = " / ".join(f"{k} {pct(v)}" for k, v in co.items())
    rows = [
        ("定价", f"起售价不超过 {below['price']:g} 万；入门版拉开价差；老车主置换补贴" if below else "定价待更多数据",
         f"{price_ceiling:g} 万起售；只出一个高配版本" if price_ceiling else "—",
         f"{price_ceiling:g} 万负面占比 {pct(next(r['neg_rate'] for r in curve if r['price'] == price_ceiling))}" if price_ceiling else ""),
        ("定位", "发布前给出三车定位对比图，按用车场景讲差异", "回避与 A8 / M7 的比较",
         f"同时提及在售车型：{sib}"),
        ("上市", "上市前两周集中释放芯片、电池、底盘信息；开放全国试驾", "爆料空窗期；与竞品发布撞期",
         f"配置期待议题 {pct(1 - by_key['spec'].neg_rate - by_key['spec'].pos_rate)} 是中性提问，释放信息就能直接回应" if "spec" in by_key else ""),
        ("传播", "讲技术代差和真实用车体验；分人群定制内容", "只讲造型；与竞品骂战",
         f"造型议题负面 {pct(by_key['design'].neg_rate)}，分歧大，不宜做主打" if "design" in by_key else ""),
    ]
    body = "".join(f"<tr><td>{a}</td><td class='do'>{escape(b)}</td><td class='dont'>{escape(c)}</td><td class='muted'>{escape(d)}</td></tr>"
                   for a, b, c, d in rows)
    return f"<table class='must'><thead><tr><th>维度</th><th>Must Do</th><th>Must Not Do</th><th>依据</th></tr></thead><tbody>{body}</tbody></table>"


def script_cards(entries: list[dict], cfg: dict, topic_names: dict) -> str:
    cards = []
    for e in entries:
        m = cfg["models"][e["model"]]
        steps = "".join(f"<li><b>{STEP_NAMES[i]}</b><span>{escape(s)}</span></li>" for i, s in enumerate(e["steps"]))
        cards.append(f"<div class='card script'><div><span class='tag'>{e['model']} · {m['strategy']}</span>"
                     f"<span class='tag' style='background:#fef2f2;color:#991b1b'>{topic_names.get(e['topic'], e['topic'])}</span></div>"
                     f"<h3 style='margin-top:8px'>{escape(e['concern'])}</h3><ol>{steps}</ol></div>")
    return "".join(cards)


def highlight(text: str, cfg: dict) -> str:
    out = escape(text)
    for rule in cfg["forbidden"]:
        out = re.sub(rule["pattern"], lambda m: f"<mark>{m.group(0)}</mark>", out)
    return out


def draft_rows(cfg: dict) -> str:
    rows = []
    for d in cfg["drafts"]:
        v = lint(d["text"], cfg)
        verdict = "<span class='ok'>可发布</span>" if not v else f"<span class='bad'>拦截 {len(v)} 处</span>"
        reasons = "".join(f"<div class='muted'>「{escape(x.match)}」：{escape(x.reason)}</div>" for x in v)
        rows.append(f"<tr><td class='muted'>{escape(d['author'])}</td><td>{highlight(d['text'], cfg)}{reasons}</td><td>{verdict}</td></tr>")
    return "".join(rows)


def render(*, raw_n, dup_n, noise_n, coded, summaries, curve, ceiling, persona_items, co,
           quality, script_cfg, playbook, playbook_issues, codebook) -> str:
    topic_names = {t["key"]: t["name"] for t in codebook["topics"]}
    price = next(s for s in summaries if s.key == "price")
    avg_p = sum(q["precision"] for q in quality.values()) / len(quality)
    avg_r = sum(q["recall"] for q in quality.values()) / len(quality)
    models = " · ".join(f"<b>{k}</b> {v['strategy']}：{escape(v['idea'])}" for k, v in script_cfg["models"].items())
    q_rows = "".join(f"<tr><td>{topic_names[k]}</td><td class='num'>{q['support']}</td><td class='num'>{q['precision']:.0%}</td><td class='num'>{q['recall']:.0%}</td></tr>"
                     for k, q in quality.items())
    ceiling_row = next((r for r in curve if r["price"] == ceiling), None)
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1" />
<title>VOC Insight Kit · 舆情洞察到销售话术</title><style>{CSS}</style></head>
<body><div class="wrap">
  <h1>VOC Insight Kit · 舆情洞察到销售话术</h1>
  <div class="meta">新车 A9 上市前的社媒评论快照：议题编码 → 点赞加权结论 → 定价 / 上市 / 传播建议 → 一线话术与合规检查
    <span class="badge">虚构品牌与车型，模拟数据</span></div>
  <div class="flow"><span>评论 + 点赞 + IP</span><i>→</i><span>去重 / 去灌水</span><i>→</i><span>议题编码</span><i>→</i><span>情感 + 点赞加权</span><i>→</i><span>问题 · 结论 · 原声</span><i>→</i><span>决策建议</span><i>→</i><span>话术 + 禁用词检查</span></div>

  <div class="grid g4" style="margin-top:18px">
    <div class="card kpi"><div class="label">有效评论</div><div class="value">{len(coded)} / {raw_n}</div><div class="sub">去重 {dup_n} 条 · 无关灌水 {noise_n} 条</div></div>
    <div class="card kpi"><div class="label">定价负面（点赞加权）</div><div class="value">{pct(price.like_neg_rate)}</div><div class="sub">按条计 {pct(price.neg_rate)}，高赞评论更负面</div></div>
    <div class="card kpi"><div class="label">心理价位关口</div><div class="value">{ceiling:g} 万</div><div class="sub">该价位负面占比 {pct(ceiling_row['neg_rate']) if ceiling_row else '—'}，首次过半</div></div>
    <div class="card kpi"><div class="label">议题编码质量</div><div class="value">{avg_p:.0%} / {avg_r:.0%}</div><div class="sub">平均精确率 / 召回率（离线评估）</div></div>
  </div>

  <h2>议题 · 结论 · 原声（按点赞占比排序）</h2>
  <div class="card"><table>
    <thead><tr><th>议题</th><th class="num">评论数</th><th class="num">点赞占比</th><th class="num">负面率</th><th>最高赞原声</th></tr></thead>
    <tbody>{topic_rows(summaries)}</tbody></table>
    <p class="muted">一条评论可以命中多个议题。点赞加权负面率 = 负面评论获赞数 / 该议题总获赞数，反映「被认同的声音」而不是「发言人数」。
    重复转发的评论合并为一条，点赞累加。</p>
  </div>

  <div class="grid g2" style="margin-top:14px">
    <div class="card">{price_svg(curve, ceiling)}
      <p class="muted">评论中提到的价格点越高，负面越多；{ceiling:g} 万是负面首次过半的价格点，深色柱为关口及以上。</p></div>
    <div class="card"><strong>潜在用户决策状态</strong>{hbars(persona_items)}
      <p class="muted" style="margin-top:12px"><strong>同时提及在售车型</strong>：{' · '.join(f'{k} {pct(v)}' for k, v in co.items())}。
      在售车型的负面会直接传导到新车讨论，上市策略要和 A8 / M7 一起定。</p></div>
  </div>

  <h2>决策建议</h2>
  <div class="card">{decisions(ceiling, curve, co, summaries)}</div>

  <h2>一线话术手册（四步回应法，按 VOC 热度排序）</h2>
  <div class="muted" style="margin-bottom:10px">{models}</div>
  <div class="grid g3">{script_cards(playbook, script_cfg, topic_names)}</div>

  <h2>禁止话术检查</h2>
  <div class="grid g2">
    <div class="card"><table><thead><tr><th>提交人</th><th>草稿</th><th>结果</th></tr></thead><tbody>{draft_rows(script_cfg)}</tbody></table></div>
    <div class="card">
      <div>话术库 {len(script_cfg['playbook'])} 条发布前检查：{'<span class="ok">0 处违规</span>' if not playbook_issues else f'<span class="bad">{len(playbook_issues)} 处违规</span>'}</div>
      <table style="margin-top:10px"><thead><tr><th>禁止规则</th><th>原因</th></tr></thead><tbody>
      {''.join(f"<tr><td><code>{escape(r['pattern'])}</code></td><td class='muted'>{escape(r['reason'])}</td></tr>" for r in script_cfg['forbidden'])}
      </tbody></table></div>
  </div>

  <h2>议题编码质量（模拟数据的真实标签，离线评估）</h2>
  <div class="card"><table><thead><tr><th>议题</th><th class="num">真实条数</th><th class="num">精确率</th><th class="num">召回率</th></tr></thead><tbody>{q_rows}</tbody></table>
    <p class="muted">关键词编码可解释、改词即生效，代价是精确率：「决策状态」「定价」会被顺带提到的词误命中。编码本见 config/codebook.toml。</p></div>

  <footer>由 run.py 生成 · 编码本 config/codebook.toml · 话术库 config/scripts.toml</footer>
</div></body></html>
"""
