# -*- coding: utf-8 -*-
"""
财务与价格数据层。价格每天刷新；财务基本面按 cache_days 缓存 (季报频率，不必天天拉)。
所有口径均为真实市场数据 (Yahoo Finance)，不做任何估读或臆造。
"""
import json, os, time, math
import numpy as np, pandas as pd, yfinance as yf
import yfsetup  # noqa: F401  (必须在 yf 调用前生效)

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA, exist_ok=True)
FCACHE = os.path.join(DATA, "fundamentals_cache.json")
CFCACHE = os.path.join(DATA, "cashflow_cache.json")

INFO_KEYS = ["currentPrice","marketCap","trailingPE","forwardPE","returnOnEquity","returnOnAssets",
             "debtToEquity","totalDebt","totalCash","ebitda","freeCashflow","operatingCashflow",
             "grossMargins","operatingMargins","profitMargins","dividendYield","payoutRatio",
             "sector","industry","beta","priceToBook","enterpriseValue","revenueGrowth",
             "earningsGrowth","totalRevenue","netIncomeToCommon","currentRatio","quickRatio",
             "shortName","fiveYearAvgDividendYield"]


def _safe(x, default=None):
    if x is None:
        return default
    try:
        f = float(x)
        return default if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return x


def load_info(tickers, cache_days=5, verbose=True):
    cache = {}
    if os.path.exists(FCACHE):
        try:
            cache = json.load(open(FCACHE))
        except Exception:
            cache = {}
    now = time.time()
    fresh, stale = {}, []
    for t in tickers:
        c = cache.get(t)
        if c and (now - c.get("_ts", 0)) < cache_days * 86400:
            fresh[t] = c
        else:
            stale.append(t)

    if verbose and stale:
        print(f"  拉取基本面 {len(stale)} 只 (缓存命中 {len(fresh)} 只)...")
    for n, t in enumerate(stale, 1):
        try:
            i = yf.Ticker(t).info or {}
            rec = {k: _safe(i.get(k)) for k in INFO_KEYS}
            rec["_ts"] = now
            fresh[t] = rec
        except Exception as e:
            if verbose:
                print(f"    ! {t}: {e}")
            fresh[t] = cache.get(t, {"_ts": now})
        if verbose and n % 20 == 0:
            print(f"    {n}/{len(stale)}")
    cache.update(fresh)
    json.dump(cache, open(FCACHE, "w"))
    return fresh


FACTORS = ["SPY", "GC=F", "CL=F", "TIP", "IEF", "^TNX"]


def load_cashflow(tickers, cache_days=30, verbose=True):
    """年度现金流历史 -> 股东盈余(自由现金流)的趋势与稳定性。
    Buffett 用 5 年滚动口径检验留存收益是否真的创造了价值，所以只看 TTM 一个点不够。"""
    cache = {}
    if os.path.exists(CFCACHE):
        try: cache = json.load(open(CFCACHE))
        except Exception: cache = {}
    now = time.time()
    stale = [t for t in tickers
             if not (cache.get(t) and (now - cache[t].get("_ts", 0)) < cache_days * 86400)]
    if verbose and stale:
        print(f"  拉取现金流历史 {len(stale)} 只 (缓存 {len(tickers)-len(stale)} 只)...")
    for n, t in enumerate(stale, 1):
        rec = {"_ts": now, "fcf": [], "ocf": []}
        try:
            cf = yf.Ticker(t).cashflow
            if cf is not None and not cf.empty:
                def grab(*names):
                    for nm in names:
                        if nm in cf.index:
                            return [None if pd.isna(v) else float(v) for v in cf.loc[nm].values]
                    return []
                fcf = grab("Free Cash Flow")
                ocf = grab("Operating Cash Flow", "Total Cash From Operating Activities")
                capex = grab("Capital Expenditure")
                if not fcf and ocf and capex:
                    fcf = [(o + c) if (o is not None and c is not None) else None
                           for o, c in zip(ocf, capex)]
                rec["fcf"], rec["ocf"] = fcf, ocf     # yfinance 列为新->旧
        except Exception as e:
            if verbose: print(f"    ! {t}: {e}")
        cache[t] = rec
        if verbose and n % 25 == 0: print(f"    {n}/{len(stale)}")
    json.dump(cache, open(CFCACHE, "w"))
    return {t: cache.get(t, {"fcf": [], "ocf": []}) for t in tickers}


def fcf_quality(rec):
    """返回 (最新/四年均值, 年化趋势, 变异系数, 连续为正年数)"""
    fcf = [v for v in (rec.get("fcf") or []) if v is not None]
    if len(fcf) < 3:
        return None, None, None, None
    arr = np.array(fcf[:4], dtype=float)          # 新->旧
    avg = arr.mean()
    latest_vs_avg = float(arr[0] / avg) if avg > 0 else None
    old_to_new = arr[::-1]
    n = len(old_to_new)
    trend = float(np.polyfit(range(n), old_to_new, 1)[0] / abs(avg)) if avg != 0 else None
    cv = float(arr.std() / abs(avg)) if avg != 0 else None
    pos_years = int(sum(1 for v in fcf if v > 0))
    return latest_vs_avg, trend, cv, pos_years


def load_prices(tickers, period="3y", verbose=True):
    want = list(tickers) + FACTORS
    px = yf.download(want, period=period, interval="1d",
                     auto_adjust=True, progress=False, threads=True)["Close"]

    # 批量下载常因 sqlite 缓存争用/限流丢票 —— 逐个补拉，不让降级数据混进评分
    missing = [t for t in want if t not in px.columns or px[t].notna().sum() < 200]
    if missing:
        if verbose:
            print(f"  批量下载缺失 {len(missing)} 只，逐个补拉: {', '.join(missing[:8])}"
                  + ("..." if len(missing) > 8 else ""))
        for t in missing:
            try:
                s = yf.Ticker(t).history(period=period, interval="1d", auto_adjust=True)["Close"]
                if len(s) >= 200:
                    s.index = s.index.tz_localize(None) if s.index.tz is not None else s.index
                    px[t] = s
            except Exception as e:
                if verbose:
                    print(f"    ! {t} 补拉失败: {e}")
        still = [t for t in want if t not in px.columns or px[t].notna().sum() < 200]
        if still and verbose:
            print(f"  仍缺失(将被排除出候选): {', '.join(still)}")
    return px.ffill()


def _beta(y: pd.Series, x: pd.Series) -> float:
    """y 对 x 的回归斜率 (最小二乘)，输入均为收益率/变动序列。"""
    j = pd.concat([y, x], axis=1).dropna()
    if len(j) < 60:
        return None
    yy, xx = j.iloc[:, 0].values, j.iloc[:, 1].values
    vx = xx.var()
    if vx == 0 or np.isnan(vx):
        return None
    return float(np.cov(yy, xx)[0, 1] / vx)


def metrics(tickers, info, px, cfh=None) -> pd.DataFrame:
    """把原始字段换算成三位框架里真正用到的指标。"""
    # 周频降噪后做因子回归
    w = px.resample("W-FRI").last()
    spy_r = px["SPY"].pct_change()
    gld_r = px["GC=F"].pct_change()
    w_spy = w["SPY"].pct_change()
    w_gld = w["GC=F"].pct_change()
    w_oil = w["CL=F"].pct_change()
    # 市场隐含盈亏平衡通胀的变动 (TIP 相对 IEF 的超额) —— 实测"通胀对冲"能力
    w_be = (w["TIP"] / w["IEF"]).pct_change()
    # 10Y 名义收益率的变动 —— 实测"名义债券久期"暴露
    w_rate = w["^TNX"].diff()
    cfh = cfh or {}
    rows = []
    for t in tickers:
        i = info.get(t, {}) or {}
        fq_lva, fq_trend, fq_cv, fq_pos = fcf_quality(cfh.get(t, {}))
        mcap = _safe(i.get("marketCap"))
        fcf  = _safe(i.get("freeCashflow"))
        ebitda = _safe(i.get("ebitda"))
        debt = _safe(i.get("totalDebt"), 0.0) or 0.0
        cash = _safe(i.get("totalCash"), 0.0) or 0.0
        ni   = _safe(i.get("netIncomeToCommon"))
        p2b  = _safe(i.get("priceToBook"))

        # Buffett 的"股东盈余"代理 = 经营现金流 - 维持性资本开支 ≈ 自由现金流
        fcf_yield = (fcf / mcap) if (fcf and mcap) else None
        # 净负债/EBITDA —— "极少或不使用负债"的量化检验
        nd_ebitda = ((debt - cash) / ebitda) if (ebitda and ebitda > 0) else None
        # ROIC 代理 = 净利 / (股东权益 + 净负债)，股东权益由 市值/PB 反推
        equity = (mcap / p2b) if (mcap and p2b and p2b > 0) else None
        ic = (equity + debt - cash) if equity is not None else None
        roic = (ni / ic) if (ni and ic and ic > 0) else None

        s = px[t].dropna() if (t in px.columns) else pd.Series(dtype=float)
        if len(s) > 250:
            r = s.pct_change()
            j = pd.concat([r, spy_r, gld_r], axis=1).dropna()
            corr_spy = float(j.iloc[:, 0].corr(j.iloc[:, 1]))
            corr_gold = float(j.iloc[:, 0].corr(j.iloc[:, 2]))
            dd = float((s / s.cummax() - 1).min())
            ret_1y = float(s.iloc[-1] / s.iloc[-252] - 1) if len(s) > 252 else None
            vs_200 = float(s.iloc[-1] / s.rolling(200).mean().iloc[-1] - 1)
            wr = w[t].pct_change()
            infl_beta = _beta(wr, w_be)      # >0 = 通胀预期上行时上涨 (真通胀对冲)
            oil_beta  = _beta(wr, w_oil)     # 高 = 大宗价格接受者
            gold_beta = _beta(wr, w_gld)
            rate_beta = _beta(wr, w_rate)    # <0 = 像名义债券 (利率上行则跌)
        else:
            corr_spy = corr_gold = dd = ret_1y = vs_200 = None
            infl_beta = oil_beta = gold_beta = rate_beta = None

        rows.append(dict(
            ticker=t, name=i.get("shortName") or t,
            sector=i.get("sector"), industry=i.get("industry"),
            price=_safe(i.get("currentPrice")), mcap=mcap,
            roe=_safe(i.get("returnOnEquity")), roic=roic,
            debt_to_equity=_safe(i.get("debtToEquity")), nd_ebitda=nd_ebitda,
            fcf_yield=fcf_yield,
            gross_margin=_safe(i.get("grossMargins")),
            op_margin=_safe(i.get("operatingMargins")),
            net_margin=_safe(i.get("profitMargins")),
            trailing_pe=_safe(i.get("trailingPE")), forward_pe=_safe(i.get("forwardPE")),
            ev_ebitda=(_safe(i.get("enterpriseValue")) / ebitda) if (ebitda and ebitda > 0
                       and _safe(i.get("enterpriseValue"))) else None,
            pb=p2b,
            div_yield=_safe(i.get("dividendYield")), payout=_safe(i.get("payoutRatio")),
            current_ratio=_safe(i.get("currentRatio")),
            rev_growth=_safe(i.get("revenueGrowth")), eps_growth=_safe(i.get("earningsGrowth")),
            beta=_safe(i.get("beta")),
            corr_spy=corr_spy, corr_gold=corr_gold, max_dd_3y=dd,
            ret_1y=ret_1y, vs_200dma=vs_200,
            infl_beta=infl_beta, oil_beta=oil_beta,
            gold_beta=gold_beta, rate_beta=rate_beta,
            fcf_vs_avg=fq_lva, fcf_trend=fq_trend, fcf_cv=fq_cv, fcf_pos_years=fq_pos,
        ))
    return pd.DataFrame(rows).set_index("ticker")


if __name__ == "__main__":
    from universe import TICKERS
    info = load_info(TICKERS)
    px = load_prices(TICKERS)
    m = metrics(TICKERS, info, px)
    m.to_csv(os.path.join(DATA, "metrics_latest.csv"))
    print(m[["roe","roic","nd_ebitda","fcf_yield","trailing_pe","gross_margin"]].head(12))
    print(f"\n{len(m)} 只; 缺失 fcf_yield: {m.fcf_yield.isna().sum()}, 缺失 roe: {m.roe.isna().sum()}")
