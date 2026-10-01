# -*- coding: utf-8 -*-
"""
问答层：用户针对某只推荐股票向 Buffett / Dimon / Dalio 追问。
回答只能依据 (1) 当天引擎对该股的真实打分与指标 (2) frameworks/*.md 的原文归纳。

配置 (环境变量，或项目根目录的 .env 文件 —— .env 已被 .gitignore，切勿提交):
  LLM_API_KEY   必填
  LLM_BASE_URL  默认 https://api.anthropic.com
  LLM_MODEL     默认 claude-opus-5
"""
import os, json, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
PERSONAS = {"buffett": "Warren Buffett", "dimon": "Jamie Dimon", "dalio": "Ray Dalio"}


def _load_dotenv():
    p = os.path.join(HERE, ".env")
    if not os.path.exists(p):
        return
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("'\"“”‘’"))


def config():
    _load_dotenv()
    return dict(key=os.environ.get("LLM_API_KEY", ""),
                base=os.environ.get("LLM_BASE_URL", "https://api.anthropic.com").rstrip("/"),
                model=os.environ.get("LLM_MODEL", "claude-opus-5"))


def _framework(who):
    return open(os.path.join(HERE, "frameworks", f"{who}_framework.md"), encoding="utf-8").read()


def _context(snap, ticker):
    row = next((r for r in snap["ranked"] if r["ticker"] == ticker), None)
    if row is None:
        raise ValueError(f"{ticker} 不在当前候选池结果中")
    m = snap["macro"]
    keep = {k: row[k] for k in ("ticker", "name", "sector", "industry", "price", "why",
                                "composite", "consensus", "weakest", "metrics")}
    for who in PERSONAS:
        keep[who] = {k: row[who][k] for k in ("score", "vetoes", "notes", "parts")}
    macro = {k: m[k] for k in ("quadrant", "ten_year", "long_bond", "growth_z", "infl_z",
                               "debasement_z", "complacency") if k in m}
    return json.dumps(dict(stock=keep, macro=macro, current_pick=snap.get("pick")),
                      ensure_ascii=False, indent=1)


def build_system(snap, ticker, who):
    names = list(PERSONAS) if who == "all" else [who]
    fw = "\n\n".join(f"===== {PERSONAS[w]} 框架 =====\n{_framework(w)}" for w in names)
    fmt = ("请分别以三位的口径各答一段，用「Buffett：」「Dimon：」「Dalio：」开头，"
           "必要时让他们互相回应或反驳。" if who == "all" else
           f"请以 {PERSONAS[who]} 的口径作答。")
    return (
        "你在模拟 Buffett、Dimon、Dalio 对一只股票的讨论。严格规则：\n"
        "1) 只依据下方【引擎数据】和【框架原文】推理；数据里没有的数字不要编造，说明“数据中没有”。\n"
        "2) 不要杜撰三人的原话或引语，用“按其框架…”的转述方式。\n"
        "3) 若引擎判定被否决，必须明确指出否决理由，不得为其辩护翻案。\n"
        "4) 这是研究讨论，不构成投资建议。用中文，简洁。\n"
        f"{fmt}\n\n【引擎数据】\n{_context(snap, ticker)}\n\n{fw}")


def _post(url, headers, body):
    req = urllib.request.Request(url, json.dumps(body).encode(), headers, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def ask(snap, ticker, who, question, history=None):
    cfg = config()
    if not cfg["key"]:
        raise RuntimeError("未配置 LLM_API_KEY，请在项目根目录 .env 中设置")
    system = build_system(snap, ticker, who)
    msgs = [m for m in (history or [])[-8:] if m.get("role") in ("user", "assistant")]
    msgs.append({"role": "user", "content": question})
    base, h = cfg["base"], {"content-type": "application/json"}
    try:      # Anthropic Messages 格式
        d = _post(f"{base}/v1/messages",
                  {**h, "x-api-key": cfg["key"], "authorization": f"Bearer {cfg['key']}",
                   "anthropic-version": "2023-06-01"},
                  dict(model=cfg["model"], max_tokens=1500, system=system, messages=msgs))
        return "".join(b.get("text", "") for b in d["content"])
    except urllib.error.HTTPError as e:
        if e.code not in (400, 404, 405):
            raise RuntimeError(f"API 错误 {e.code}: {e.read().decode()[:300]}")
    # 回退: OpenAI 兼容格式 (部分中转站只提供这个)
    try:
        d = _post(f"{base}/v1/chat/completions", {**h, "authorization": f"Bearer {cfg['key']}"},
                  dict(model=cfg["model"], max_tokens=1500,
                       messages=[{"role": "system", "content": system}] + msgs))
        return d["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"API 错误 {e.code}: {e.read().decode()[:300]}")
