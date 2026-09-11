# -*- coding: utf-8 -*-
"""把每日快照渲染成自包含 HTML 仪表盘 (无外部依赖，离线可看)。"""
import json, html, datetime as dt

CSS = """
:root{--bg:#0d1117;--panel:#161b22;--panel2:#1c2330;--line:#2a3038;--tx:#e6edf3;--dim:#8b949e;
--acc:#f0b429;--ok:#3fb950;--bad:#f85149;--warn:#d29922;--b:#4493f8;--d:#a371f7;--r:#f0883e;}
@media(prefers-color-scheme:light){:root{--bg:#f6f8fa;--panel:#fff;--panel2:#f0f3f6;--line:#d8dee4;
--tx:#1f2328;--dim:#636c76;--acc:#9a6700;}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--tx);font:14px/1.55 -apple-system,"SF Pro Text",
"Helvetica Neue","PingFang SC","Microsoft YaHei",sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:1240px;margin:0 auto;padding:26px 22px 70px}
.mono{font-family:"SF Mono",ui-monospace,Menlo,monospace;font-variant-numeric:tabular-nums}
h1{font-size:19px;margin:0;letter-spacing:.2px}
h2{font-size:13px;text-transform:uppercase;letter-spacing:1.4px;color:var(--dim);
margin:32px 0 12px;font-weight:600}
.top{display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:10px;
border-bottom:1px solid var(--line);padding-bottom:14px}
.sub{color:var(--dim);font-size:12px}
.badge{display:inline-block;padding:3px 9px;border-radius:11px;font-size:11px;font-weight:600;
letter-spacing:.4px}
.bg-hold{background:rgba(63,185,80,.15);color:var(--ok);border:1px solid rgba(63,185,80,.35)}
.bg-sw{background:rgba(240,136,62,.15);color:var(--r);border:1px solid rgba(240,136,62,.4)}
.bg-none{background:rgba(248,81,73,.15);color:var(--bad);border:1px solid rgba(248,81,73,.4)}
.bg-q{background:rgba(240,180,41,.13);color:var(--acc);border:1px solid rgba(240,180,41,.35)}
.hero{background:linear-gradient(150deg,var(--panel) 0%,var(--panel2) 100%);
border:1px solid var(--line);border-radius:13px;padding:24px 26px;margin-top:18px;
display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);gap:26px}
@media(max-width:820px){.hero{grid-template-columns:1fr}}
.tk{font-size:46px;font-weight:700;letter-spacing:-1.2px;line-height:1}
.nm{color:var(--dim);font-size:13px;margin-top:5px}
.px{font-size:24px;margin-top:14px;font-weight:600}
.kv{display:grid;grid-template-columns:auto 1fr;gap:5px 16px;font-size:12.5px;margin-top:16px}
.kv b{color:var(--dim);font-weight:500}
.rsn{background:rgba(240,180,41,.07);border-left:3px solid var(--acc);padding:11px 14px;
border-radius:0 7px 7px 0;font-size:13px;margin-top:4px}
.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
@media(max-width:900px){.cards{grid-template-columns:1fr}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:11px;padding:17px 18px}
.card.b{border-top:3px solid var(--b)}.card.d{border-top:3px solid var(--d)}
.card.r{border-top:3px solid var(--r)}
.who{font-size:15px;font-weight:700;margin-bottom:2px}
.role{font-size:11px;color:var(--dim);margin-bottom:12px}
.sc{font-size:30px;font-weight:700;line-height:1}.sc small{font-size:13px;color:var(--dim);font-weight:400}
.bars{margin:13px 0 11px}
.bar{display:grid;grid-template-columns:74px 1fr 38px;gap:8px;align-items:center;
font-size:11px;margin-bottom:5px;color:var(--dim)}
.track{height:7px;background:var(--line);border-radius:3px;overflow:hidden}
.fill{height:100%;border-radius:3px}
.quote{font-size:12.5px;line-height:1.6;border-top:1px solid var(--line);padding-top:11px;margin-top:4px}
.ev{font-size:11.5px;color:var(--dim);margin-top:9px;line-height:1.65}
.ev div{padding-left:11px;text-indent:-11px}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th{text-align:right;color:var(--dim);font-weight:600;font-size:10.5px;text-transform:uppercase;
letter-spacing:.7px;padding:7px 9px;border-bottom:1px solid var(--line)}
th:first-child,td:first-child{text-align:left}
td{padding:8px 9px;border-bottom:1px solid rgba(128,128,128,.13);text-align:right}
tr:hover td{background:rgba(128,128,128,.05)}
.pick-row td{background:rgba(240,180,41,.08)!important;font-weight:600}
.scroll{overflow-x:auto;border:1px solid var(--line);border-radius:10px;background:var(--panel)}
.grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:11px}
@media(max-width:860px){.grid4{grid-template-columns:repeat(2,1fr)}}
.mt{background:var(--panel);border:1px solid var(--line);border-radius:9px;padding:13px 15px}
.mt .l{font-size:10.5px;color:var(--dim);text-transform:uppercase;letter-spacing:.7px}
.mt .v{font-size:21px;font-weight:700;margin-top:3px}
.mt .n{font-size:11px;color:var(--dim);margin-top:3px}
.pos{color:var(--ok)}.neg{color:var(--bad)}.wr{color:var(--warn)}
.note{font-size:11.5px;color:var(--dim);line-height:1.75}
.note code{background:var(--panel2);padding:1px 5px;border-radius:4px;font-size:11px}
.vt{font-size:11.5px;color:var(--dim)}
"""

def _f(v, fmt="{:.2f}", dash="—"):
    return dash if v is None else fmt.format(v)

def _bar(label, val, mx, color):
    pct = 0 if not mx else max(0, min(100, val / mx * 100))
    return (f'<div class="bar"><span>{label}</span><span class="track">'
            f'<span class="fill" style="width:{pct:.0f}%;background:{color}"></span></span>'
            f'<span class="mono">{val:.0f}</span></div>')

def _card(kind, who, role, color, sc, parts, maxes, quote, notes, vetoes):
    bars = "".join(_bar(k, v, maxes.get(k, 30), color) for k, v in parts.items())
    ev = "".join(f"<div>· {html.escape(n)}</div>" for n in notes if n)
    vt = ""
    if vetoes:
        vt = ('<div class="ev" style="color:var(--bad)">'
              + "".join(f"<div>✗ {html.escape(v)}</div>" for v in vetoes) + "</div>")
    return f"""<div class="card {kind}"><div class="who">{who}</div><div class="role">{role}</div>
<div class="sc">{sc:.0f}<small>/100</small></div><div class="bars">{bars}</div>
<div class="quote">{quote}</div><div class="ev">{ev}</div>{vt}</div>"""


def verdicts(p, mac):
    """把各自框架里的量化结论，用三人各自的说话方式落成一句判词。"""
    m, b, d, a = p["metrics"], p["buffett"], p["dimon"], p["dalio"]
    tk = p["ticker"]
    roe = _f(m["roe"], "{:.1%}"); nd = _f(m["nd_ebitda"], "{:.2f}")
    fy = _f(m["fcf_yield"], "{:.2%}"); pe = _f(m["trailing_pe"], "{:.1f}")
    ten = mac["ten_year"]
    bq = (f"「一家几乎不用借钱就能赚 {roe} 净资产回报的生意，净负债只有 EBITDA 的 {nd} 倍。"
          f"我付出的价格换回 {fy} 的股东盈余，而长期国债给我 {ten:.2f}%——"
          f"这笔账算得过来，但也就是算得过来而已。」")
    dq = (f"「{pe} 倍市盈率，在我看到的 23 倍市场里这是少数还没被抬起来的角落。"
          f"资产负债表扛得住压力测试——这是我唯一在意的事。」")
    aq = (f"「实测通胀 beta {_f(m['infl_beta'],'{:+.2f}')}：通胀预期上行时它涨，这才叫真对冲，"
          f"不是嘴上说的定价权。利率 beta {_f(m['rate_beta'],'{:+.3f}')}，它不是伪装成股票的名义债券。」")
    return bq, dq, aq


def build(snap, path, web_public=False):
    mac, ranked = snap["macro"], snap["ranked"]
    pick = snap["pick"]
    P = next((r for r in ranked if r["ticker"] == pick), None)
    passing = [r for r in ranked if r["consensus"]]
    act = snap["action"]
    bcls = {"HOLD": "bg-hold", "SWITCH": "bg-sw", "INIT": "bg-sw"}.get(act, "bg-none")

    REPO = "frankfang2025/three-wise-men"
    banner = ""
    if web_public:
        banner = f"""<div style="background:rgba(68,147,248,.09);border:1px solid rgba(68,147,248,.3);
border-radius:10px;padding:12px 16px;margin-bottom:16px;font-size:12.5px;line-height:1.7">
<b>这是云端自动生成的页面。</b>每个交易日美股收盘后由 GitHub Actions 跑完引擎自动更新，
无需任何本地程序。当前数据抓取于 <b>{snap['run_at'][:16].replace('T',' ')}</b>（UTC 时区的 runner 时钟）。
<a href="https://github.com/{REPO}/actions/workflows/daily.yml" target="_blank"
 style="color:var(--b);text-decoration:none;font-weight:600">→ 立即手动跑一次</a>
（跳转 GitHub，点 Run workflow，约 2 分钟后刷新本页）
 · <a href="https://github.com/{REPO}" target="_blank"
 style="color:var(--dim);text-decoration:none">源码</a>
 · <a href="data/latest.json" style="color:var(--dim);text-decoration:none">JSON</a></div>"""

    head = f"""{banner}<div class="top"><div><h1>三人共识选股 · Buffett × Dimon × Dalio</h1>
<div class="sub">依据 NotebookLM 三本笔记本原文框架 · 实时市场数据 · {snap['date']} 刷新于 {snap['run_at'][11:16]}</div></div>
<div><span class="badge bg-q">{html.escape(mac['quadrant'])}</span>
<span class="badge {bcls}" style="margin-left:6px">{act}</span></div></div>"""

    if P is None:
        hero = f'<div class="hero"><div><div class="tk">空仓</div><div class="rsn">{html.escape(snap["reason"])}</div></div></div>'
        cards = ""
    else:
        m = P["metrics"]
        bq, dq, aq = verdicts(P, mac)
        hero = f"""<div class="hero"><div>
<div class="tk mono">{P['ticker']}</div><div class="nm">{html.escape(P['name'])} · {html.escape(P['sector'] or '')} / {html.escape(P['industry'] or '')}</div>
<div class="px mono">${_f(m['price'] if 'price' in m else P['price'],'{:.2f}')}
<span class="sub" style="font-size:12px;margin-left:9px">市值 ${_f(m['mcap'] and m['mcap']/1e9,'{:.0f}')}B</span></div>
<div class="kv mono"><b>综合分</b><span>{P['composite']} <span class="sub">(0.45×最低分 + 0.55×均值)</span></span>
<b>最弱环节</b><span>{P['weakest']}</span>
<b>持有自</b><span>{snap.get('since') or '—'}</span>
<b>通过共识</b><span>{len(passing)} / {len(ranked)} 只候选</span></div></div>
<div><div class="sub" style="margin-bottom:7px">本次决策</div>
<div class="rsn">{html.escape(snap['reason'])}</div>
<div class="kv mono" style="margin-top:15px">
<b>ROE</b><span>{_f(m['roe'],'{:.1%}')}</span><b>ROIC</b><span>{_f(m['roic'],'{:.1%}')}</span>
<b>净负债/EBITDA</b><span>{_f(m['nd_ebitda'],'{:.2f}')}x</span><b>负债/权益</b><span>{_f(m['debt_to_equity'],'{:.0f}')}%</span>
<b>股东盈余收益率</b><span>{_f(m['fcf_yield'],'{:.2%}')} <span class="sub">vs 10Y {mac['ten_year']:.2f}%</span></span>
<b>市盈率</b><span>{_f(m['trailing_pe'],'{:.1f}')}x <span class="sub">(前瞻 {_f(m['forward_pe'],'{:.1f}')}x)</span></span>
<b>实测通胀β</b><span>{_f(m['infl_beta'],'{:+.2f}')}</span><b>实测利率β</b><span>{_f(m['rate_beta'],'{:+.3f}')}</span>
<b>β / 与标普相关</b><span>{_f(m['beta'])} / {_f(m['corr_spy'])}</span></div></div></div>"""

        BM = {"ROE": 25, "杠杆": 20, "定价权": 15, "估值": 30, "可预测性": 10}
        DM = {"主题": 35, "资产负债表": 25, "估值": 20, "尾部韧性": 20}
        RM = {"象限契合": 35, "实物资产": 20, "通胀对冲": 25, "分散化": 20}
        cards = ('<h2>三人各自的判词</h2><div class="cards">'
                 + _card("b", "Warren Buffett", "生意质地 × 价格纪律", "var(--b)",
                         P["buffett"]["score"], P["buffett"]["parts"], BM, bq,
                         P["buffett"]["notes"], P["buffett"]["vetoes"])
                 + _card("d", "Jamie Dimon", "宏观主题 × 堡垒资产负债表", "var(--d)",
                         P["dimon"]["score"], P["dimon"]["parts"], DM, dq,
                         P["dimon"]["notes"], P["dimon"]["vetoes"])
                 + _card("r", "Ray Dalio", "债务周期象限 × 实测通胀对冲", "var(--r)",
                         P["dalio"]["score"], P["dalio"]["parts"], RM, aq,
                         P["dalio"]["notes"], P["dalio"]["vetoes"])
                 + "</div>")

    gz, iz = mac["growth_z"], mac["infl_z"]
    macro_html = f"""<h2>实时宏观状态机</h2><div class="grid4">
<div class="mt"><div class="l">Dalio 四象限</div><div class="v" style="font-size:15px">{html.escape(mac['quadrant'])}</div>
<div class="n">增长 z {gz:+.2f} · 通胀 z {iz:+.2f}</div></div>
<div class="mt"><div class="l">Buffett 的机会成本</div><div class="v mono">{mac['ten_year']:.2f}%</div>
<div class="n">10Y 国债 · 30Y {mac['long_bond']:.2f}% · 股东盈余收益率须打赢它</div></div>
<div class="mt"><div class="l">货币贬值读数</div><div class="v mono {'wr' if mac['debasement_z']>0.8 else ''}">{mac['debasement_z']:+.2f}</div>
<div class="n">黄金 ${mac['gold']:,.0f} · &gt;0.8 则名义债券为"坏资产"</div></div>
<div class="mt"><div class="l">Dimon 的信用利差警戒</div><div class="v mono {'wr' if mac['credit_tightness_z']>1.2 else ''}">{mac['credit_tightness_z']:+.2f}</div>
<div class="n">越高越像他说的"极度收紧" · VIX {mac['vix']:.1f}</div></div></div>
<div class="note" style="margin-top:11px">象限由市场价格实时推出：增长轴 = 铜金比 + 信用偏好(HYG/IEF) + 周期/防御(XLI/XLU) + 趋势；
通胀轴 = 盈亏平衡通胀(TIP/IEF) + 实际金价 + 原油 + 美元 + 期限溢价。
当前曲线为<b>{'熊陡（长端上行驱动）' if mac['bear_steepening'] else '牛陡/平坦'}</b>，
{'因此陡峭被计入通胀轴而非增长轴 —— 这是财政与通胀风险溢价，不是复苏信号。' if mac['bear_steepening'] else ''}</div>"""

    def row(r, pick=False):
        m = r["metrics"]
        return (f'<tr class="{"pick-row" if pick else ""}"><td class="mono"><b>{r["ticker"]}</b> '
                f'<span class="sub">{html.escape((r["name"] or "")[:22])}</span></td>'
                f'<td class="mono"><b>{r["composite"]:.1f}</b></td>'
                f'<td class="mono">{r["buffett"]["score"]:.0f}</td><td class="mono">{r["dimon"]["score"]:.0f}</td>'
                f'<td class="mono">{r["dalio"]["score"]:.0f}</td>'
                f'<td class="mono">{_f(m["roe"],"{:.0%}")}</td><td class="mono">{_f(m["nd_ebitda"],"{:.1f}")}x</td>'
                f'<td class="mono">{_f(m["fcf_yield"],"{:.1%}")}</td><td class="mono">{_f(m["trailing_pe"],"{:.0f}")}x</td>'
                f'<td class="mono">{_f(m["infl_beta"],"{:+.1f}")}</td>'
                f'<td class="vt" style="text-align:left">{html.escape(r["why"][:30])}</td></tr>')

    tbl = ('<h2>通过三人共识的全部标的</h2><div class="scroll"><table><tr>'
           '<th>标的</th><th>综合</th><th>巴菲特</th><th>Dimon</th><th>Dalio</th>'
           '<th>ROE</th><th>净负债/EBITDA</th><th>股东盈余率</th><th>PE</th><th>通胀β</th>'
           '<th style="text-align:left">入选逻辑</th></tr>'
           + "".join(row(r, r["ticker"] == pick) for r in passing) + "</table></div>")

    rej = [r for r in ranked if not r["consensus"]]
    rej.sort(key=lambda x: -x["composite"])
    def rrow(r):
        vs = []
        for who, k in [("巴菲特", "buffett"), ("Dimon", "dimon"), ("Dalio", "dalio")]:
            for v in r[k]["vetoes"]:
                vs.append(f"<b style='color:var(--bad)'>{who}</b> {html.escape(v)}")
        return (f'<tr><td class="mono"><b>{r["ticker"]}</b> <span class="sub">{html.escape((r["name"] or "")[:20])}</span></td>'
                f'<td class="mono">{r["composite"]:.1f}</td>'
                f'<td class="vt" style="text-align:left">{" ‖ ".join(vs[:2])}</td></tr>')
    vetos = ('<h2>被否决的名字 · 谁、因为什么</h2>'
             '<div class="note" style="margin-bottom:9px">三位是"与"关系：任何一人否决即出局。'
             '这一栏往往比入选名单更能说明问题。</div>'
             '<div class="scroll"><table><tr><th>标的</th><th>综合</th>'
             '<th style="text-align:left">否决理由（引各自框架原话口径）</th></tr>'
             + "".join(rrow(r) for r in rej[:26]) + "</table></div>")

    log = snap.get("log", [])
    loghtml = ""
    if log:
        loghtml = ('<h2>换股记录</h2><div class="scroll"><table><tr><th>日期</th><th>从</th><th>换到</th>'
                   '<th style="text-align:left">原因</th></tr>'
                   + "".join(f'<tr><td class="mono">{l["date"]}</td><td class="mono">{l.get("from") or "—"}</td>'
                             f'<td class="mono"><b>{l["to"]}</b></td>'
                             f'<td class="vt" style="text-align:left">{html.escape(l["reason"])}</td></tr>'
                             for l in reversed(log)) + "</table></div>")

    method = f"""<h2>方法与口径</h2><div class="note">
<b>三套框架的来源</b>：Buffett 1977–2024 年致股东信（255 份来源）、Ray Dalio 原则与债务周期（118 份）、
Jamie Dimon 2025–26 达沃斯发言与股东信（165 份），经 NotebookLM 检索归纳后落在
<code>frameworks/*.md</code>；每条门槛都对应其中的原始表述。<br><br>
<b>为什么是"与"不是"平均"</b>：题目要求三人<b>都</b>认可，所以任一人否决即出局；
综合分用 <code>0.45×最低分 + 0.55×均值</code>，防止"两人极满意、一人勉强"的名字靠平均分蒙混过关。<br><br>
<b>标签 vs 实测</b>：通胀对冲能力不采用主观标签，而是对市场隐含盈亏平衡通胀（TIP/IEF）做周频回归得到
<code>通胀β</code>——因为微观定价权不等于股价能对冲通胀（例：可口可乐品牌定价权很强，但实测通胀β为 −0.49）。
利率β用于识别"伪装成股票的名义债券"（公用事业普遍为负），这是 Dalio 在货币贬值期明确点名要回避的。<br><br>
<b>换股规则</b>：在任被任一人否决 → 立即换；挑战者综合分领先 ≥5 分且连续 3 个交易日 → 换；其余持有。<br><br>
<b>数据源</b>：Yahoo Finance（价格、财报、现金流量表），全部为真实市场数据，无估读。
财务基本面缓存 5 天、现金流量表缓存 30 天，价格与宏观每次运行实时拉取。<br><br>
<b>已知局限</b>：① 主题标签（实物资产强度、Dimon 主题归属）仍是人工判断；
② 保险公司的自由现金流含浮存金流入，股东盈余口径偏高；
③ ROIC 用"市值/市净率"反推股东权益，为代理指标；
④ 利息保障倍数未逐一取数，以净负债/EBITDA 与负债权益比替代；
⑤ 本页是框架推演，<b>不构成投资建议</b>。</div>"""

    doc = (f'<!doctype html><html lang="zh"><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width,initial-scale=1">'
           f'<title>三人共识选股 · {snap["date"]}</title><style>{CSS}</style></head><body><div class="wrap">'
           + head + hero + cards + macro_html + tbl + vetos + loghtml + method
           + '</div></body></html>')
    open(path, "w").write(doc)
    return path
