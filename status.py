# -*- coding: utf-8 -*-
"""快速查看当前结论，不重新拉数据。用法: python3 status.py"""
import json, os
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
d = json.load(open(os.path.join(D, "latest.json")))
P = next((r for r in d["ranked"] if r["ticker"] == d["pick"]), None)
m = d["macro"]
print(f"\n  日期 {d['date']} (数据刷新于 {d['run_at'][11:16]})")
print(f"  象限 {m['quadrant']}")
print(f"  10Y {m['ten_year']:.2f}%  30Y {m['long_bond']:.2f}%  黄金 ${m['gold']:,.0f}  贬值读数 {m['debasement_z']:+.2f}\n")
if P:
    x = P["metrics"]
    print(f"  ★ {P['ticker']}  {P['name']}   ${P['price'] or 0:.2f}")
    print(f"    综合 {P['composite']}   巴菲特 {P['buffett']['score']} | Dimon {P['dimon']['score']} | Dalio {P['dalio']['score']}"
          f"   最弱环节: {P['weakest']}")
    print(f"    ROE {x['roe']:.1%}  净负债/EBITDA {x['nd_ebitda']:.2f}x  股东盈余率 {x['fcf_yield']:.2%}"
          f"  PE {x['trailing_pe']:.1f}x  通胀β {x['infl_beta']:+.2f}")
print(f"\n  [{d['action']}] {d['reason']}")
print(f"\n  通过共识的其余标的: " + ", ".join(
    f"{r['ticker']}({r['composite']})" for r in d["ranked"] if r["consensus"] and r["ticker"] != d["pick"]))
if d.get("log"):
    print("\n  换股记录:")
    for l in reversed(d["log"]):
        print(f"    {l['date']}  {l.get('from') or '—'} → {l['to']}: {l['reason']}")
print()
