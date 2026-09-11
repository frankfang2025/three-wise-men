# -*- coding: utf-8 -*-
"""
每日刷新入口。
  python3 run_daily.py            日常刷新 (基本面走缓存, 价格/宏观实时)
  python3 run_daily.py --full     强制重拉全部基本面
换股规则 (避免每天追分数导致来回换):
  1) 在任持仓被任一人否决 -> 立即换 (硬性)
  2) 挑战者综合分领先在任 >= 5.0 分, 且连续 3 个交易日成立 -> 换
  3) 其余情况一律持有
"""
import json, os, sys, datetime as dt
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
DATA = os.path.join(HERE, "data")
os.makedirs(DATA, exist_ok=True)
STATE = os.path.join(DATA, "state.json")
HIST = os.path.join(DATA, "history.jsonl")

SWITCH_MARGIN = 5.0
SWITCH_DAYS = 3


def load_state():
    if os.path.exists(STATE):
        return json.load(open(STATE))
    return {"pick": None, "since": None, "challenger": None, "challenger_dates": [], "log": []}


def decide(state, ranked):
    """返回 (pick_ticker, action, reason)"""
    passing = [r for r in ranked if r["consensus"]]
    today = dt.date.today().isoformat()

    if not passing:
        return None, "NO_CONSENSUS", "当前没有任何标的能同时通过三人的否决门 —— 空仓等待"

    top = passing[0]
    cur = state.get("pick")

    if cur is None:
        return top["ticker"], "INIT", f"首次建仓: {top['ticker']} 综合分 {top['composite']}"

    cur_row = next((r for r in ranked if r["ticker"] == cur), None)

    # 规则1: 在任被否决
    if cur_row is None:
        return top["ticker"], "SWITCH", f"{cur} 已不在候选池，换为 {top['ticker']}"
    if not cur_row["consensus"]:
        vs = cur_row["buffett"]["vetoes"] + cur_row["dimon"]["vetoes"] + cur_row["dalio"]["vetoes"]
        return top["ticker"], "SWITCH", (f"在任 {cur} 被否决 ({'; '.join(vs[:2])})，"
                                         f"立即换为 {top['ticker']}")

    # 规则2: 挑战者持续领先
    if top["ticker"] != cur:
        lead = top["composite"] - cur_row["composite"]
        if lead >= SWITCH_MARGIN:
            # 按"不同日期"计数而非运行次数 —— 否则同一天手动连点几次刷新
            # 就能凑满 3 次触发换股，防churn机制形同虚设
            dates = set(state.get("challenger_dates", [])) if state.get("challenger") == top["ticker"] else set()
            dates.add(today)
            state["challenger"] = top["ticker"]
            state["challenger_dates"] = sorted(dates)
            n = len(dates)
            if n >= SWITCH_DAYS:
                return top["ticker"], "SWITCH", (f"{top['ticker']} 综合分领先在任 {cur} "
                                                 f"{lead:.1f} 分，且已在 {n} 个不同交易日持续领先，触发换股")
            return cur, "HOLD", (f"{top['ticker']} 领先 {lead:.1f} 分 (已观察 {n}/{SWITCH_DAYS} 个交易日)，"
                                 f"暂继续持有 {cur}")
        state["challenger"] = None
        state["challenger_dates"] = []
        return cur, "HOLD", f"{cur} 仍通过三人检验，领先者 {top['ticker']} 差距仅 {lead:.1f} 分，未达换股阈值"

    state["challenger"] = None
    state["challenger_dates"] = []
    return cur, "HOLD", f"{cur} 仍是三人共识下的第一名 (综合分 {cur_row['composite']})"


def main(full=False):
    import macro, fundamentals, scoring
    from universe import TICKERS

    print("1/4 读取实时宏观状态...")
    mac = macro.regime(macro.fetch())
    print(f"    10Y {mac['ten_year']:.2f}% | 30Y {mac['long_bond']:.2f}% | 黄金 ${mac['gold']:,.0f}")
    print(f"    象限: {mac['quadrant']} (增长 z={mac['growth_z']:+.2f}, 通胀 z={mac['infl_z']:+.2f})")

    print(f"2/4 拉取 {len(TICKERS)} 只候选的基本面与价格...")
    info = fundamentals.load_info(TICKERS, cache_days=0 if full else 5)
    cfh = fundamentals.load_cashflow(TICKERS, cache_days=0 if full else 30)
    px = fundamentals.load_prices(TICKERS)
    m = fundamentals.metrics(TICKERS, info, px, cfh)

    # 数据完整性护栏: 云端 runner 可能被 Yahoo 限流，宁可整轮失败也不能发布残缺结果
    have = int(m["infl_beta"].notna().sum())
    need = int(len(TICKERS) * 0.80)
    print(f"    数据完整性: {have}/{len(TICKERS)} 只拿到完整因子")
    if have < need:
        raise SystemExit(f"数据完整性不足 ({have}/{len(TICKERS)}，需≥{need})："
                         f"疑似被限流，本轮中止且不覆盖已有结果")

    print("3/4 三人独立打分 + 否决...")
    ranked = scoring.score_all(m, mac)
    passing = [r for r in ranked if r["consensus"]]
    print(f"    通过三人共识: {len(passing)}/{len(ranked)}")

    print("4/4 应用换股规则...")
    state = load_state()
    prev = state.get("pick")
    pick, action, reason = decide(state, ranked)
    today = dt.date.today().isoformat()
    if pick != prev:
        state["pick"] = pick
        state["since"] = today
        state["challenger"] = None
        state["challenger_dates"] = []
        state.setdefault("log", []).append({"date": today, "from": prev, "to": pick, "reason": reason})
    state["last_run"] = dt.datetime.now().isoformat(timespec="seconds")
    json.dump(state, open(STATE, "w"), ensure_ascii=False, indent=2)

    snap = {"date": today, "run_at": state["last_run"], "macro": mac,
            "pick": pick, "action": action, "reason": reason,
            "since": state.get("since"), "log": state.get("log", []),
            "ranked": ranked}
    json.dump(snap, open(os.path.join(DATA, "latest.json"), "w"), ensure_ascii=False, indent=2)
    with open(HIST, "a") as f:
        f.write(json.dumps({"date": today, "run_at": state["last_run"], "pick": pick,
                            "action": action, "reason": reason,
                            "composite": next((r["composite"] for r in ranked if r["ticker"] == pick), None),
                            "quadrant": mac["quadrant"], "ten_year": mac["ten_year"],
                            "n_pass": len(passing)}, ensure_ascii=False) + "\n")

    import render, notify
    dash = os.path.join(HERE, "dashboard.html")
    render.build(snap, dash)

    # GitHub Pages 托管的副本（docs/ 是 Pages 的发布目录）
    docs = os.path.join(HERE, "docs")
    os.makedirs(os.path.join(docs, "data"), exist_ok=True)
    render.build(snap, os.path.join(docs, "index.html"), web_public=True)
    json.dump(snap, open(os.path.join(docs, "data", "latest.json"), "w"),
              ensure_ascii=False, indent=2)

    notify.deliver(snap, dash)

    print(f"\n{'='*68}\n  结论: {pick}  [{action}]\n  {reason}\n{'='*68}")
    print(f"\n  通过三人共识的前 10 名:")
    for r in passing[:10]:
        print(f"    {r['ticker']:6s} {r['composite']:5.1f}  "
              f"B{r['buffett']['score']:5.1f} D{r['dimon']['score']:5.1f} R{r['dalio']['score']:5.1f}  "
              f"{r['name'][:28]}")
    return snap


if __name__ == "__main__":
    main(full="--full" in sys.argv)
