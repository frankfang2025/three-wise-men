# -*- coding: utf-8 -*-
"""
三人评分引擎。核心设计: 三位是"与"关系 —— 任何一人否决即出局，
最终分用 0.45*min + 0.55*mean，防止"两人极满意、一人勉强"的名字靠平均分蒙混过关。

每条门槛与权重都对应 frameworks/*.md 中该人物的原始表述，注释里标出依据。
"""
import numpy as np
from universe import U

# Buffett 明确回避的行业关键词 (buffett_framework.md 第6节)
BUFFETT_EXCLUDE_INDUSTRY = [
    "airline", "textile", "steel", "biotechnology", "drug manufacturers—specialty",
    "shell companies", "mortgage", "asset management",
]


def _ramp(x, lo, hi, out_lo, out_hi):
    """把 x 从 [lo,hi] 线性映射到 [out_lo,out_hi]，超出部分截断。"""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return out_lo
    if hi == lo:
        return out_hi
    return float(np.clip((x - lo) / (hi - lo), 0, 1) * (out_hi - out_lo) + out_lo)


# ============================== BUFFETT ==============================
def score_buffett(r, tag, mac):
    """依据: ROE门槛12-25%、极少负债、股东盈余、盈利收益率须优于长期无风险利率、
    特许权定价权、回避大宗同质化与能力圈外行业。"""
    v, notes = [], []
    ten = mac["ten_year"] / 100.0

    roe, nd, de = r.roe, r.nd_ebitda, r.debt_to_equity
    fcfy, gm = r.fcf_yield, r.gross_margin
    ind = r.industry if isinstance(r.industry, str) else ""
    ind = ind.lower()

    # ---- 否决门 ----
    if not tag["circle"]:
        v.append("能力圈外: " + (tag["why"].split("——")[-1].strip() if "——" in tag["why"]
                 else "无法预判未来10-20年的经济特征"))
    if any(k in ind for k in BUFFETT_EXCLUDE_INDUSTRY):
        v.append(f"明确回避的行业: {r.industry}")
    if roe is None or roe < 0.12:
        v.append(f"ROE {roe:.1%} 低于12%的'良好回报'门槛" if roe is not None else "ROE 数据缺失")
    if nd is not None and nd > 3.5:
        v.append(f"净负债/EBITDA {nd:.1f}x 违背'极少或不使用负债'")
    if de is not None and de > 150:
        v.append(f"负债/权益 {de:.0f}% 过高，ROE 靠杠杆而非生意本身")
    if fcfy is None or fcfy <= 0:
        v.append("股东盈余为负 (自由现金流不足以覆盖维持性资本开支)")
    elif fcfy < ten * 0.85:
        v.append(f"股东盈余收益率 {fcfy:.2%} 打不过 {mac['ten_year']:.2f}% 的无风险国债")
    # 他回避的是"没有成本优势的"大宗同质化行业 —— 用实测油价beta判断是否纯价格接受者
    ob = getattr(r, "oil_beta", None)
    if ob is not None and ob > 0.80:
        v.append(f"实测油价beta {ob:.2f} —— 纯大宗价格接受者，利润由价格而非生意决定")

    # ---- 打分 ----
    s_roe = _ramp(roe, 0.12, 0.40, 8, 25)                       # 12%→及格, 25%+→喜诗糖果档
    if nd is None:
        s_lev = 12.0
    elif nd <= 0:   s_lev = 20.0                                 # 净现金
    elif nd <= 1:   s_lev = 17.0
    elif nd <= 2:   s_lev = 13.0
    elif nd <= 3:   s_lev = 8.0
    else:           s_lev = 4.0
    s_gm = _ramp(gm, 0.20, 0.60, 2, 15)                          # 毛利率 = 定价权代理
    ratio = (fcfy / ten) if (fcfy and ten > 0) else 0
    s_val = _ramp(ratio, 0.85, 2.0, 6, 30)                       # 相对无风险利率的安全边际
    # 股东盈余的持久性: 他用5年滚动口径，萎缩中的现金流不配拿满分估值分
    tr, lva, pos = getattr(r,"fcf_trend",None), getattr(r,"fcf_vs_avg",None), getattr(r,"fcf_pos_years",None)
    if tr is not None:
        s_val *= float(np.clip(1 + 0.45 * np.clip(tr, -0.6, 0.4), 0.55, 1.15))
        notes.append(f"股东盈余四年趋势 {tr:+.0%}/年" +
                     ("（萎缩中，估值分已按比例下调）" if tr < -0.05 else
                      "（增长中）" if tr > 0.05 else "（大致持平）"))
    if lva is not None and lva < 0.7:
        notes.append(f"最新自由现金流仅为四年均值的 {lva:.0%} —— 当期收益率有高估之嫌")
    if pos is not None and pos < 3:
        v.append(f"近四年仅 {pos} 年自由现金流为正 —— 股东盈余不稳定")
    s_pred = _ramp(-(r.max_dd_3y or -0.5), 0.15, 0.60, 10, 2) if r.max_dd_3y else 5
    # 商品价格敏感度越高，未来10-20年经济特征越不可预测 -> 扣可预测性
    if ob is not None:
        s_pred -= _ramp(ob, 0.15, 0.80, 0, 4)
    s_pred = float(np.clip(s_pred, 0, 10))
    if ob is not None:
        notes.append(f"实测油价beta {ob:.2f}" + ("（成本优势型，非纯价格接受者）" if ob <= 0.5 else "（商品价格敏感）"))

    notes.append(f"ROE {roe:.1%}" if roe else "ROE n/a")
    notes.append(f"净负债/EBITDA {nd:.1f}x" if nd is not None else "杠杆 n/a")
    notes.append(f"股东盈余收益率 {fcfy:.2%} vs 10Y {mac['ten_year']:.2f}% (倍数 {ratio:.2f}x)"
                 if fcfy else "股东盈余 n/a")
    notes.append(f"毛利率 {gm:.0%}" if gm else "")
    if "insurance" in ind:
        notes.append("注: 保险公司自由现金流含浮存金流入，股东盈余口径需打折看待")
    return dict(score=round(s_roe + s_lev + s_gm + s_val + s_pred, 1),
                vetoes=v, notes=[n for n in notes if n],
                parts=dict(ROE=round(s_roe,1), 杠杆=round(s_lev,1), 定价权=round(s_gm,1),
                           估值=round(s_val,1), 可预测性=round(s_pred,1)))


# ============================== DIMON ==============================
DIMON_THEME_W = {           # dimon_framework.md 第三节"看好/战略加码的行业"
    "energy_lng": 9, "grid_infra": 9, "datacenter_power": 8, "defense": 8,
    "cyber": 7, "gold_real": 7, "fortress_div": 6, "bank_fortress": 5, "ai_incumbent": 6,
}
DIMON_ANTI = {              # 他明确警示的领域
    "trad_software": "传统软件 —— 他警告是下个信贷周期的意外受害者",
    "private_credit": "私人信贷 1.8万亿，缺透明度、未经坏市场压力测试",
    "cre": "商业地产 —— 高利率+经济放缓下承压严重",
}


def score_dimon(r, tag, mac):
    """依据: 看好能源独立/LNG、电网基础设施、国防、网安、黄金实物；
    警示传统软件/私人信贷/CRE/高杠杆；强调堡垒式资产负债表与尾部压力测试；
    并指出股票估值已在'历史区间上限'(23倍PE)、信用利差'极度收紧'。"""
    v, notes = [], []
    for a in tag["anti"]:
        v.append(DIMON_ANTI.get(a, a))

    nd, pe, cr = r.nd_ebitda, r.trailing_pe, r.current_ratio
    if nd is not None and nd > 4.0:
        v.append(f"净负债/EBITDA {nd:.1f}x —— 达不到'堡垒式资产负债表'")
    if pe is not None and pe > 30:
        v.append(f"PE {pe:.1f}x 远超他点名的23倍'估值区间上限'")
    if pe is None or pe <= 0:
        v.append("无正的市盈率 (盈利为负)")

    # 主题契合
    raw = sum(DIMON_THEME_W.get(t, 0) for t in tag["dimon"])
    s_theme = _ramp(raw, 0, 18, 0, 35)
    # 堡垒资产负债表
    s_bs = 0.0
    s_bs += 15.0 if nd is None else (15 if nd <= 0 else _ramp(-nd, -4, 0, 2, 15))
    s_bs += _ramp(cr, 0.6, 2.0, 2, 10) if cr else 5
    # 估值 vs 他的 23 倍警戒线
    s_val = _ramp(-(pe or 40), -30, -10, 0, 20)
    # 尾部韧性: 他要求按"股市跌50%、利率到8%"做压力测试
    s_tail = _ramp(-(r.beta or 1.2), -1.5, -0.4, 0, 12)
    s_tail += _ramp(-(r.max_dd_3y or -0.6), 0.15, 0.60, 8, 0) if r.max_dd_3y else 4

    notes.append("主题: " + ("/".join(tag["dimon"]) if tag["dimon"] else "无"))
    notes.append(f"PE {pe:.1f}x vs 他警戒的23x" if pe else "PE n/a")
    notes.append(f"净负债/EBITDA {nd:.1f}x" if nd is not None else "")
    notes.append(f"beta {r.beta:.2f}, 3年最大回撤 {r.max_dd_3y:.0%}"
                 if (r.beta and r.max_dd_3y) else "")
    return dict(score=round(s_theme + s_bs + s_val + s_tail, 1),
                vetoes=v, notes=[n for n in notes if n],
                parts=dict(主题=round(s_theme,1), 资产负债表=round(s_bs,1),
                           估值=round(s_val,1), 尾部韧性=round(s_tail,1)))


# ============================== DALIO ==============================
def score_dalio(r, tag, mac):
    """依据: 长债务周期末期应回避法币现金与名义债券、偏好硬通货与实物/生产性资产;
    四象限决定该持有什么; 优质企业股权(能随通胀提价)优于房地产; 强调低相关分散。

    关键: 通胀对冲能力用"实测"而非标签 —— 对市场隐含盈亏平衡通胀(TIP/IEF)做回归,
    因为微观定价权不等于股价能对冲通胀 (例: KO 有定价权但 infl_beta 为负)。
    """
    v, notes = [], []
    q = mac["quadrant_key"]
    real, infl_tag = tag["real"], tag["infl"]
    ib = getattr(r, "infl_beta", None)
    gb = getattr(r, "gold_beta", None)
    rb = getattr(r, "rate_beta", None)

    W = mac.get("quadrant_weights") or {mac["quadrant_key"]: 1.0}
    infl_up = mac.get("infl_up_conf", 1.0 if "up" in q.split("_")[1] else 0.0)

    # ---- 否决门 ----
    if real < 2 and (ib is None or ib < 0.3):
        v.append(f"既非实物/生产性资产(real={real})，实测通胀beta "
                 + (f"{ib:.2f} 也不具通胀对冲能力" if ib is not None else "亦缺失"))
    if infl_up > 0.6 and ib is not None and ib < -0.2:
        v.append(f"通胀上行置信度 {infl_up:.0%}，但实测通胀beta {ib:.2f} 为负 —— 通胀上行时反而下跌")
    # 货币贬值期最忌名义债券型资产 (他称之为"坏资产")
    if mac["debasement_z"] > 0.8 and rb is not None and rb < -0.05:
        v.append(f"实测利率beta {rb:.3f} —— 属名义债券代理，"
                 f"货币贬值读数 {mac['debasement_z']:.2f} 下是他明确点名的'坏资产'")

    # ---- 打分 ----
    # 象限契合 (0-35): 四象限各算一遍，再按置信度加权混合，避免临界跳变
    q_uu = _ramp(ib, -0.3, 2.5, 0, 26) + _ramp(real, 0, 3, 1, 9)
    q_du = q_uu
    q_ud = 16 + _ramp(real, 0, 3, 2, 8) + _ramp(-(r.beta or 1), -1.6, -0.6, 0, 11)
    q_dd = _ramp(-(r.beta or 1.2), -1.4, -0.4, 2, 20) + _ramp(real, 0, 3, 2, 15)
    s_q = (W.get("up_up",0)*q_uu + W.get("down_up",0)*q_du
           + W.get("up_down",0)*q_ud + W.get("down_down",0)*q_dd)
    s_q = float(np.clip(s_q, 0, 35))

    s_real = _ramp(real, 0, 3, 0, 20)

    # 通胀对冲 (0-25): 实测为主(18) + 黄金暴露(7)
    s_hedge = _ramp(ib, -0.3, 2.5, 0, 18) + _ramp(gb, -0.05, 0.8, 0, 7)

    # 分散化 (0-20): "圣杯是15个以上互不相关的回报流"
    s_div = _ramp(-(r.corr_spy if r.corr_spy is not None else 0.7), -0.85, -0.20, 0, 14)
    s_div += _ramp(abs(rb) if rb is not None else 0.05, 0.06, 0.0, 0, 6)

    notes.append(f"象限 {mac['quadrant']}")
    notes.append(f"实测通胀beta {ib:+.2f}" + ("（真通胀对冲）" if (ib or 0) > 1 else "") if ib is not None else "")
    notes.append(f"实测利率beta {rb:+.3f}" + ("（非债券代理）" if (rb or 0) >= 0 else "（偏债券代理）") if rb is not None else "")
    notes.append(f"实物资产强度 {real}/3；与标普相关 {r.corr_spy:.2f}"
                 if r.corr_spy is not None else f"实物资产强度 {real}/3")
    return dict(score=round(s_q + s_real + s_hedge + s_div, 1),
                vetoes=v, notes=[n for n in notes if n],
                parts=dict(象限契合=round(s_q,1), 实物资产=round(s_real,1),
                           通胀对冲=round(s_hedge,1), 分散化=round(s_div,1)))


def score_all(m, mac):
    """对全池打分，返回按综合分排序的结果列表。"""
    out = []
    for t, r in m.iterrows():
        tag = U.get(t)
        if not tag:
            continue
        if r.price is None or (isinstance(r.price,float) and np.isnan(r.price)) \
           or getattr(r, "infl_beta", None) is None:
            continue          # 数据不完整的标的不参与共识评选
        b = score_buffett(r, tag, mac)
        d = score_dimon(r, tag, mac)
        a = score_dalio(r, tag, mac)
        scores = [b["score"], d["score"], a["score"]]
        vetoed = bool(b["vetoes"] or d["vetoes"] or a["vetoes"])
        composite = round(0.45 * min(scores) + 0.55 * float(np.mean(scores)), 1)
        out.append(dict(
            ticker=t, name=(r["name"] if isinstance(r["name"], str) else t),
            sector=(r.sector if isinstance(r.sector, str) else None),
            industry=(r.industry if isinstance(r.industry, str) else None),
            price=r.price, why=tag["why"],
            buffett=b, dimon=d, dalio=a,
            composite=composite, consensus=not vetoed,
            weakest=["Buffett","Dimon","Dalio"][int(np.argmin(scores))],
            metrics={k: (None if (r[k] is None or (isinstance(r[k], float) and np.isnan(r[k]))) else float(r[k]))
                     for k in ["roe","roic","nd_ebitda","debt_to_equity","fcf_yield","gross_margin",
                               "op_margin","trailing_pe","forward_pe","ev_ebitda","div_yield",
                               "beta","corr_spy","corr_gold","max_dd_3y","ret_1y","vs_200dma","mcap",
                               "infl_beta","oil_beta","gold_beta","rate_beta"]},
        ))
    out.sort(key=lambda x: (x["consensus"], x["composite"]), reverse=True)
    return out
