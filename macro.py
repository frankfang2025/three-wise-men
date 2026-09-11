# -*- coding: utf-8 -*-
"""
实时宏观状态机 —— 把 Dalio 的"经济机器四象限"和 Buffett 的"无风险利率门槛"
从市场价格里实时推出来，而不是写死。

输出:
  long_bond      30年美债收益率  -> Buffett 的折现率/机会成本锚
  ten_year       10年美债收益率  -> Buffett 的盈利收益率对照基准
  growth_z       增长动能 z 分   -> Dalio 四象限的横轴
  infl_z         通胀动能 z 分   -> Dalio 四象限的纵轴
  quadrant       四象限名称 + 该象限的偏好资产 (来自 dalio_framework.md 的表)
  credit_z       信用利差松紧    -> Dimon 说的"利差极度收紧"警戒
  complacency    市场自满度      -> Dimon 说的"水涨船高"与2005-07类比
"""
import numpy as np, pandas as pd, yfinance as yf
import yfsetup  # noqa: F401

SERIES = {
    "tnx": "^TNX",      # 10Y
    "tyx": "^TYX",      # 30Y
    "irx": "^IRX",      # 13W
    "gold": "GC=F",
    "copper": "HG=F",
    "oil": "CL=F",
    "dxy": "DX-Y.NYB",
    "vix": "^VIX",
    "hyg": "HYG",       # 高收益债
    "ief": "IEF",       # 7-10Y 国债
    "tip": "TIP",       # 通胀挂钩债 -> TIP/IEF 比值即市场隐含盈亏平衡通胀
    "xli": "XLI",       # 周期
    "xlu": "XLU",       # 防御
    "spy": "SPY",
}

# Dalio 四象限 -> 偏好资产 (frameworks/dalio_framework.md 第二节原表)
QUADRANT_ASSETS = {
    ("up","up"):     ("增长上行 + 通胀上行", ["大宗商品","黄金","TIPS","实物资产股权"]),
    ("up","down"):   ("增长上行 + 通胀下行 (金发姑娘)", ["股票","公司债","名义债券"]),
    ("down","up"):   ("增长下行 + 通胀上行 (滞胀)", ["黄金","TIPS","大宗商品","有定价权的生产性资产"]),
    ("down","down"): ("增长下行 + 通胀下行 (衰退/通缩)", ["名义国债","现金/短债"]),
}


def _z(s: pd.Series, win: int = 756, cap: float = 2.5) -> float:
    """最新值相对过去 win 天分布的 z 分，截断在 ±cap 以免单一信号失真后主导整轴。"""
    s = s.dropna()
    if len(s) < 60:
        return 0.0
    tail = s.tail(win)
    sd = tail.std()
    if sd == 0 or np.isnan(sd):
        return 0.0
    return float(np.clip((s.iloc[-1] - tail.mean()) / sd, -cap, cap))


def _mom(s: pd.Series, days: int) -> pd.Series:
    return s / s.shift(days) - 1.0


def fetch(period="5y"):
    df = yf.download(list(SERIES.values()), period=period, interval="1d",
                     auto_adjust=True, progress=False, threads=True)["Close"]
    df = df.rename(columns={v: k for k, v in SERIES.items()}).ffill()
    return df


def regime(df: pd.DataFrame) -> dict:
    last = df.iloc[-1]

    # ---------- 增长轴 ----------
    # 铜金比: 工业需求 vs 避险，经典增长代理
    cg   = _z(_mom(df["copper"] / df["gold"], 63))
    # 信用偏好: 高收益债跑赢国债 = 愿意承担企业风险
    cred = _z(_mom(df["hyg"] / df["ief"], 63))
    # 周期股 vs 公用事业: 板块轮动确认
    cyc  = _z(_mom(df["xli"] / df["xlu"], 63))
    # 股指相对200日均线: 广义风险偏好
    trend = _z(df["spy"] / df["spy"].rolling(200).mean())

    # 曲线斜率要分清牛陡/熊陡 —— 只有短端下行驱动的牛陡才是宽松/复苏信号；
    # 长端上行驱动的熊陡是财政与通胀风险溢价，应计入通胀轴而非增长轴。
    slope = df["tnx"] - df["irx"]
    d_slope = float(slope.iloc[-1] - slope.iloc[-64])
    d_long  = float(df["tyx"].iloc[-1] - df["tyx"].iloc[-64])
    bear_steepening = d_slope > 0 and d_long > 0
    curve_growth = 0.0 if bear_steepening else 0.5 * _z(slope)

    growth_z = float(np.mean([cg, cred, cyc, 0.5 * trend, curve_growth]))

    # ---------- 通胀轴 ----------
    # 盈亏平衡通胀代理 (TIP/IEF): 水平和动能各半，这是最直接的市场隐含通胀信号
    be_lvl = _z(df["tip"] / df["ief"])
    be_mom = _z(_mom(df["tip"] / df["ief"], 126))
    be = 0.5 * be_lvl + 0.5 * be_mom
    # 实际金价 (黄金/通胀挂钩债): 用水平而非动能 —— 大涨后的横盘不等于通胀消退
    real_gold = _z(df["gold"] / df["tip"])
    # 原油动能
    oil = _z(_mom(df["oil"], 126))
    # 美元走弱 = 输入型通胀
    usd = -_z(_mom(df["dxy"], 126))
    # 熊陡贡献: 长端被财政/通胀风险溢价推高
    term_prem = _z(slope) if bear_steepening else 0.0

    infl_z = float(np.mean([be, real_gold, 0.7 * oil, 0.5 * usd, 0.7 * term_prem]))

    # 用 sigmoid 把两轴转成连续权重，取代"大于0就是上行"的刀刃式分类 ——
    # z 在零点附近时任何噪音都会让象限来回翻，而象限直接驱动配置结论。
    def _sig(z, k=0.40):
        return float(1 / (1 + np.exp(-z / k)))
    g_w, i_w = _sig(growth_z), _sig(infl_z)          # = 处于"上行"的置信度
    weights = {"up_up": g_w * i_w, "up_down": g_w * (1 - i_w),
               "down_up": (1 - g_w) * i_w, "down_down": (1 - g_w) * (1 - i_w)}
    dom = max(weights, key=weights.get)
    g, i = dom.split("_")
    qname, qassets = QUADRANT_ASSETS[(g, i)]
    # 任一轴落在中性带内，就如实标注为过渡状态，不假装确定
    neutral = []
    if abs(growth_z) < 0.25: neutral.append("增长")
    if abs(infl_z) < 0.25:  neutral.append("通胀")
    if neutral:
        qname += f"（{'/'.join(neutral)}轴接近中性，象限判定不稳）"

    # ---------- Dalio: 长债务周期末期/货币贬值读数 ----------
    # 硬货币相对法币计价资产走强 + 长端收益率高企 + 熊陡 = 债务货币化特征
    debasement = float(np.mean([
        real_gold,
        _z(df["gold"] / df["spy"]),
        _z(df["tyx"]),
        term_prem,
    ]))

    # ---------- Dimon 的两个警戒表 ----------
    credit_z = _z(df["hyg"] / df["ief"])          # 越高 = 利差越紧 = 越像2005-07
    vix_z    = _z(df["vix"])
    complacency = float(np.mean([credit_z, -vix_z, trend]))

    return {
        "long_bond": float(last["tyx"]),
        "ten_year": float(last["tnx"]),
        "t_bill": float(last["irx"]),
        "gold": float(last["gold"]),
        "spy": float(last["spy"]),
        "vix": float(last["vix"]),
        "growth_inputs": {"copper_gold": cg, "credit_appetite": cred,
                          "cyclical": cyc, "trend": trend, "curve": curve_growth},
        "infl_inputs": {"breakeven": be, "real_gold": real_gold, "oil": oil,
                        "usd_weak": usd, "term_premium": term_prem},
        "bear_steepening": bear_steepening,
        "growth_z": growth_z, "infl_z": infl_z,
        "growth_up_conf": g_w, "infl_up_conf": i_w,
        "quadrant_weights": weights, "neutral_axes": neutral,
        "quadrant": qname, "quadrant_key": dom, "preferred_assets": qassets,
        "debasement_z": debasement,
        "credit_tightness_z": credit_z,
        "complacency": complacency,
    }


if __name__ == "__main__":
    import json
    r = regime(fetch())
    print(json.dumps(r, indent=2, ensure_ascii=False))
