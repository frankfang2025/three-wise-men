# -*- coding: utf-8 -*-
"""
候选股票池 —— 依据三位的框架预筛出"有可能同时被三人接受"的名字。

每个标的的标注含义：
  dimon : Dimon 明确看好的主题标签 (正面)；anti 为他明确警示的领域 (负面)
  real  : Dalio 口径的"实物/生产性资产"强度 0-3
  infl  : 通胀转嫁能力 0-3 (能否随通胀提价而不流失销量 —— 也是 Buffett 的特许权检验)
  circle: 是否落在 Buffett 的能力圈内 (未来10-20年经济特征可预测)
  why   : 一句话说明为什么它可能同时满足三人

标签来源见 frameworks/*.md (由 NotebookLM 三本笔记本原文归纳)。
"""

# Dimon 正面主题
T_ENERGY = "energy_lng"          # 能源独立 / LNG
T_GRID = "grid_infra"            # 电网 / 基础设施
T_DC = "datacenter_power"        # 数据中心供电
T_DEF = "defense"                # 国防 / 重新武装化
T_CYBER = "cyber"                # 网络安全
T_GOLD = "gold_real"             # 黄金 / 实物商品
T_FORT = "fortress_div"          # 堡垒资产负债表 + 股息增长的大型企业
T_BANK = "bank_fortress"         # 金融 (他自己的领域)
T_AI = "ai_incumbent"            # 有资金和数据的 AI 受益在位者

# Dimon 负面主题 (直接一票否决)
A_SOFT = "trad_software"         # 传统软件 —— 他警告是下个信贷周期的意外受害者
A_PC = "private_credit"          # 私人信贷 1.8万亿，缺透明度未经压力测试
A_CRE = "cre"                    # 商业地产

U = {}

def add(t, dimon=(), anti=(), real=0, infl=0, circle=True, why=""):
    U[t] = dict(dimon=list(dimon), anti=list(anti), real=real, infl=infl,
                circle=circle, why=why)

# ---------- 能源 / LNG / 中游 (Dimon: 能源独立+LNG; Dalio: 实物资产抗通胀) ----------
add("XOM",  (T_ENERGY,T_FORT), real=3, infl=3, why="一体化规模成本优势+实物储量，通胀直接转嫁")
add("CVX",  (T_ENERGY,T_FORT), real=3, infl=3, why="Buffett 现实持仓；低杠杆一体化油气")
add("COP",  (T_ENERGY,),       real=3, infl=3, why="低成本页岩+LNG 出口敞口")
add("OXY",  (T_ENERGY,),       real=3, infl=3, why="Buffett 持股约28%；二叠纪低成本+CCUS")
add("EOG",  (T_ENERGY,),       real=3, infl=3, why="页岩里最低成本、几乎零净负债")
add("PSX",  (T_ENERGY,),       real=3, infl=2, why="炼化+中游现金流")
add("WMB",  (T_ENERGY,T_GRID), real=3, infl=3, why="天然气管道，费率含通胀调整条款，像收费桥")
add("KMI",  (T_ENERGY,T_GRID), real=3, infl=3, why="管道网络，长约照付不议")
add("OKE",  (T_ENERGY,T_GRID), real=3, infl=3, why="NGL 管道+处理，费率型")
add("LNG",  (T_ENERGY,),       real=3, infl=2, why="Dimon 点名 LNG；照付不议固定费")
add("TRGP", (T_ENERGY,),       real=3, infl=3, why="二叠纪集输处理")
add("TPL",  (T_ENERGY,T_GOLD), real=3, infl=3, why="纯土地权利金，零资本开支，近乎无负债")
add("EPD",  (T_ENERGY,T_GRID), real=3, infl=3, why="中游龙头，费率含PPI联动 (注意MLP的K-1税务)")

# ---------- 电网 / 电力 / 数据中心供电 (Dimon 重点: 电网升级+AI电力需求) ----------
add("NEE",  (T_GRID,T_DC),     real=3, infl=2, why="受监管电网+可再生，费率基数随通胀重定价")
add("DUK",  (T_GRID,),         real=3, infl=2, why="受监管公用事业，费率基数模式")
add("SO",   (T_GRID,T_DC),     real=3, infl=2, why="东南部负荷增长最快，数据中心集中地")
add("AEP",  (T_GRID,T_DC),     real=3, infl=2, why="输电资产+数据中心接入队列")
add("D",    (T_GRID,T_DC),     real=3, infl=2, why="弗吉尼亚数据中心走廊")
add("XEL",  (T_GRID,),         real=3, infl=2, why="受监管电网")
add("WEC",  (T_GRID,),         real=3, infl=2, why="受监管电网")
add("ETR",  (T_GRID,T_DC),     real=3, infl=2, why="墨西哥湾工业+数据中心负荷")
add("CEG",  (T_DC,),           real=3, infl=2, why="核电直供数据中心 (但市电价格敞口大)")
add("VST",  (T_DC,),           real=3, infl=2, why="核电+燃气机组，AI电力受益")
add("PWR",  (T_GRID,),         real=2, infl=2, why="电网施工，Dimon 的电网升级直接承包方")
add("ETN",  (T_GRID,T_DC),     real=2, infl=2, why="电气设备，数据中心配电")
add("EMR",  (T_GRID,T_DC),     real=2, infl=2, why="自动化+电力管理")
add("HUBB", (T_GRID,T_DC),     real=2, infl=2, why="电网组件，定价权强")
add("AME",  (T_GRID,),         real=2, infl=2, why="利基仪器，高毛利")
add("ROK",  (T_GRID,),         real=2, infl=2, why="工业自动化")
add("PH",   (T_GRID,T_DEF),    real=2, infl=2, why="流体控制+航空航天售后")
add("GEV",  (T_GRID,T_DC),     real=2, infl=2, why="燃气轮机+电网设备订单积压")
add("VRT",  (T_DC,), circle=False, real=2, infl=2, why="数据中心热管理 (技术迭代快，超出能力圈)")

# ---------- 国防 / 航空航天 (Dimon: 全球重新武装化) ----------
add("LMT",  (T_DEF,),          real=2, infl=2, why="重新武装化主承包商，成本加成合同转嫁通胀")
add("RTX",  (T_DEF,),          real=2, infl=3, why="发动机售后备件定价权强")
add("NOC",  (T_DEF,),          real=2, infl=2, why="核三位一体+B-21 长周期订单")
add("GD",   (T_DEF,),          real=2, infl=2, why="造船+湾流，订单积压可见度高")
add("LHX",  (T_DEF,),          real=2, infl=2, why="通信电子")
add("HII",  (T_DEF,),          real=3, infl=2, why="唯一核动力航母船厂，实物壁垒")
add("TDG",  (T_DEF,),          real=2, infl=3, why="航空售后寡头，年年提价不掉量 —— 典型特许权")
add("HEI",  (T_DEF,),          real=2, infl=3, why="PMA 备件，定价权强")

# ---------- 网络安全 (Dimon 视为最大系统性威胁之一) ----------
add("PANW", (T_CYBER,), circle=False, real=0, infl=1, why="Dimon 看好网安，但技术迭代快不在 Buffett 能力圈")
add("FTNT", (T_CYBER,), circle=False, real=0, infl=1, why="同上")
add("CRWD", (T_CYBER,), circle=False, real=0, infl=1, why="同上，且估值极高")
add("CHKP", (T_CYBER,), circle=False, real=0, infl=1, why="同上")

# ---------- 黄金 / 权利金 (Dimon: 央行购金; Dalio: 建议配置5-15%) ----------
add("FNV",  (T_GOLD,),         real=3, infl=3, why="黄金权利金，零负债零资本开支，92%毛利")
add("WPM",  (T_GOLD,),         real=3, infl=3, why="流式权利金，无运营成本敞口")
add("RGLD", (T_GOLD,),         real=3, infl=3, why="权利金模式")
add("AEM",  (T_GOLD,), circle=False, real=3, infl=3, why="矿业是价格接受者+重资本，Buffett 明确回避的大宗同质化行业")
add("NEM",  (T_GOLD,), circle=False, real=3, infl=3, why="同上")

# ---------- 铁路 (Buffett 自己买下 BNSF 的那类"收费桥") ----------
add("UNP",  (T_FORT,T_GRID),   real=3, infl=3, why="Buffett 亲自买下同行 BNSF；实物路网+核心定价权")
add("CSX",  (T_FORT,T_GRID),   real=3, infl=3, why="东部双寡头之一")
add("NSC",  (T_FORT,T_GRID),   real=3, infl=3, why="东部双寡头之一")
add("CP",   (T_FORT,T_GRID),   real=3, infl=3, why="唯一贯通北美三国的路网")
add("CNI",  (T_FORT,T_GRID),   real=3, infl=3, why="加拿大干线")

# ---------- 必需服务 / 定价权高于CPI ----------
add("WM",   (T_FORT,),         real=3, infl=3, why="垃圾填埋场不可复制，提价长期高于CPI")
add("RSG",  (T_FORT,),         real=3, infl=3, why="同上，环卫寡头")
add("WCN",  (T_FORT,),         real=3, infl=3, why="二三线市场独家经营")
add("VMC",  (T_FORT,),         real=3, infl=3, why="骨料是本地垄断 (运输半径限制)，提价能力极强")
add("MLM",  (T_FORT,),         real=3, infl=3, why="同上，骨料+基建法案受益")
add("LIN",  (T_FORT,),         real=2, infl=3, why="工业气体现场制气，15年长约含能源与通胀转嫁条款")
add("APD",  (T_FORT,),         real=2, infl=3, why="工业气体，长约模式")
add("ECL",  (T_FORT,),         real=1, infl=3, why="水处理+清洁，渗透式提价")
add("SHW",  (T_FORT,),         real=1, infl=3, why="涂料分销网络，品牌定价权")
add("HON",  (T_FORT,T_GRID),   real=2, infl=2, why="多元工业+航空售后")
add("ITW",  (T_FORT,),         real=2, infl=2, why="80/20 模式，高ROIC")
add("DOV",  (T_FORT,),         real=2, infl=2, why="多元工业")
add("CTAS", (T_FORT,),         real=1, infl=3, why="制服租赁，路线密度护城河")
add("FAST", (T_FORT,),         real=1, infl=2, why="现场库存管理粘性")
add("GWW",  (T_FORT,),         real=1, infl=2, why="MRO 分销规模")
add("URI",  (T_FORT,),         real=3, infl=2, why="设备租赁实物资产池")

# ---------- 必需消费 (Buffett 的经典特许权) ----------
add("KO",   (T_FORT,),         real=1, infl=3, why="Buffett 持仓37年；全球品牌定价权")
add("PEP",  (T_FORT,),         real=1, infl=3, why="零食+饮料双引擎")
add("PG",   (T_FORT,),         real=1, infl=3, why="日用品牌矩阵")
add("CL",   (T_FORT,),         real=1, infl=3, why="口腔护理全球份额")
add("MDLZ", (T_FORT,),         real=1, infl=3, why="全球零食品牌")
add("MO",   (T_FORT,),         real=1, infl=3, why="极端定价权 (销量下滑但提价覆盖)")
add("PM",   (T_FORT,),         real=1, infl=3, why="无烟产品转型+定价权")
add("MCD",  (T_FORT,),         real=2, infl=3, why="实质是地产+特许经营权利金")
add("COST", (T_FORT,),         real=2, infl=2, why="会员费模式，通缩式让利换忠诚")
add("WMT",  (T_FORT,),         real=2, infl=2, why="规模成本优势")

# ---------- 金融 (Dimon 自己的领域；Buffett 长期重仓保险) ----------
add("BRK-B",(T_FORT,T_BANK),   real=2, infl=2, why="Buffett 本人的载体，现金堡垒")
add("JPM",  (T_BANK,T_AI),     real=1, infl=2, why="Dimon 本人掌舵；AI 在位者+堡垒资产负债表")
add("PGR",  (T_BANK,),         real=1, infl=2, why="车险定价模型领先，承保利润率高")
add("CB",   (T_BANK,),         real=1, infl=2, why="财险定价周期受益")
add("TRV",  (T_BANK,),         real=1, infl=2, why="商业财险")
add("AJG",  (T_BANK,),         real=1, infl=3, why="保险经纪，佣金随保费通胀同步上涨")
add("MMC",  (T_BANK,),         real=1, infl=3, why="经纪+咨询，轻资产高ROE")
add("AFL",  (T_BANK,),         real=1, infl=1, why="补充健康险")
add("ALL",  (T_BANK,),         real=1, infl=2, why="车险家财险")

# ---------- 【扩充】AI 与科技龙头 (此前整体缺席，导致结论系统性偏向能源/实物资产) ----------
# circle 判断: 现金流稳定、护城河已被十年以上验证的平台型公司视为在能力圈内 (Buffett 自己是苹果最大持仓之一);
# 技术路线仍在剧烈迭代的半导体设备/设计与网安维持 False，由数据而非偏见去检验其它两位的看法。
add("AAPL", (T_AI,T_FORT),  real=1, infl=2, why="Buffett 长期核心持仓；生态锁定+巨额回购，现金堡垒")
add("MSFT", (T_AI,T_FORT),  real=1, infl=2, why="云+企业软件订阅，AI 在位者，有资金有数据 (Dimon: AI 受益在位者)")
add("GOOGL",(T_AI,T_FORT),  real=1, infl=2, why="搜索垄断+云+自研芯片，现金流充沛")
add("AMZN", (T_AI,),        real=2, infl=2, why="云 AWS+物流网络，实物基础设施厚")
add("META", (T_AI,),        real=1, infl=2, why="广告现金牛，AI 推荐引擎；资本开支大需检验股东盈余")
add("NVDA", (T_AI,T_DC), circle=False, real=1, infl=2, why="AI 算力垄断；技术迭代快，估值与周期性是主要风险")
add("AVGO", (T_AI,T_DC), circle=False, real=1, infl=2, why="定制 AI 芯片+基础设施软件")
add("TSM",  (T_AI,T_DC), circle=False, real=3, infl=2, why="先进制程垄断；重资产实物工厂，但有地缘风险")
add("AMAT", (T_AI,), circle=False, real=2, infl=2, why="半导体设备，周期性强")
add("LRCX", (T_AI,), circle=False, real=2, infl=2, why="刻蚀设备，周期性强")
add("KLAC", (T_AI,), circle=False, real=2, infl=2, why="良率检测设备，份额极高")
add("V",    (T_FORT,T_AI),  real=0, infl=2, why="支付网络收费桥，轻资产，Buffett 曾持有")
add("MA",   (T_FORT,T_AI),  real=0, infl=2, why="支付网络收费桥，轻资产高 ROE")

# ---------- 【扩充】医疗 (必需性强、定价权来自专利/规模) ----------
add("JNJ",  (T_FORT,),      real=1, infl=2, why="多元医疗，AAA 级资产负债表")
add("LLY",  (T_FORT,),      real=1, infl=2, why="GLP-1 需求；估值高、竞争与政策风险")
add("ABBV", (T_FORT,),      real=1, infl=2, why="免疫类现金牛；专利悬崖风险")
add("MRK",  (T_FORT,),      real=1, infl=2, why="肿瘤管线；专利悬崖风险")
add("ABT",  (T_FORT,),      real=1, infl=2, why="医疗器械+诊断，股息增长")
add("SYK",  (T_FORT,),      real=1, infl=2, why="骨科器械，院内粘性与定价权")
add("ISRG", (T_FORT,),      real=1, infl=2, why="手术机器人，耗材+服务经常性收入")
add("TMO",  (T_FORT,),      real=1, infl=2, why="科研与制药供应链的“卖铲人”")
add("ZTS",  (T_FORT,),      real=1, infl=3, why="动物保健龙头，提价能力强")
add("UNH",  (T_FORT,),      real=1, infl=2, why="医保管理+服务，规模优势；政策监管风险")

# ---------- 【扩充】消费与零售 ----------
add("HD",   (T_FORT,),      real=2, infl=2, why="家居建材零售龙头，规模成本优势")
add("LOW",  (T_FORT,),      real=2, infl=2, why="同上，双寡头之一")
add("TJX",  (T_FORT,),      real=2, infl=2, why="折扣零售，经济下行期反而受益")
add("ORLY", (T_FORT,),      real=2, infl=3, why="汽配售后，必需维修需求，提价能力强")
add("AZO",  (T_FORT,),      real=2, infl=3, why="同上")
add("NKE",  (T_FORT,),      real=1, infl=2, why="全球品牌；近年增长承压")
add("BKNG", (T_FORT,),      real=0, infl=2, why="在线旅游平台，轻资产高现金流")
add("MNST", (T_FORT,),      real=1, infl=3, why="能量饮料品牌，定价权强")

# ---------- 【扩充】金融 (银行本是 Dimon 的主场，此前仅有 JPM) ----------
add("BAC",  (T_BANK,),      real=1, infl=2, why="美国大型银行，Buffett 曾重仓")
add("WFC",  (T_BANK,),      real=1, infl=2, why="大型银行")
add("AXP",  (T_BANK,),      real=1, infl=2, why="Buffett 长期持仓；封闭式支付网络+高端客群")
add("SPGI", (T_FORT,),      real=0, infl=3, why="信用评级与指数垄断，定价权极强")
add("MCO",  (T_FORT,),      real=0, infl=3, why="信用评级双寡头，Buffett 长期持仓")
add("CME",  (T_FORT,),      real=0, infl=2, why="衍生品交易所，网络效应")
add("ICE",  (T_FORT,),      real=0, infl=2, why="交易所+数据")

# ---------- 【扩充】工业与重型设备 ----------
add("CAT",  (T_GRID,T_DC),  real=3, infl=2, why="重型设备，电力与基建投资受益；周期性")
add("DE",   (T_FORT,),      real=3, infl=2, why="农机龙头，精准农业；周期性")
add("GE",   (T_DEF,),       real=2, infl=3, why="航空发动机售后服务，长约定价")
add("TT",   (T_GRID,T_DC),  real=2, infl=2, why="暖通制冷，数据中心散热受益")
add("ADP",  (T_FORT,),      real=0, infl=2, why="薪资外包，客户粘性强，浮存金利息")

# ---------- 明确的反面样本 (留在池中以验证否决逻辑确实生效) ----------
add("CRM",  anti=(A_SOFT,), circle=False, real=0, infl=1, why="传统软件 —— Dimon 明确警示的 AI 颠覆对象")
add("ORCL", anti=(A_SOFT,), circle=False, real=1, infl=1, why="传统软件+数据中心债务扩张")
add("ARCC", anti=(A_PC,),   circle=False, real=0, infl=1, why="私人信贷 BDC —— Dimon 点名的1.8万亿风险区")
add("BXP",  anti=(A_CRE,),  circle=False, real=3, infl=1, why="写字楼 CRE —— Dimon 警示高息下承压")

TICKERS = sorted(U.keys())

if __name__ == "__main__":
    print(f"候选池 {len(TICKERS)} 只")
    from collections import Counter
    c = Counter(th for v in U.values() for th in v["dimon"])
    for k, n in c.most_common():
        print(f"  {k:18s} {n}")
    print("  反面样本:", [t for t, v in U.items() if v["anti"]])
