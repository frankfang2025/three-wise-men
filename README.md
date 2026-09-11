# 三人共识选股 · Buffett × Dimon × Dalio

## → https://frankfang2025.github.io/three-wise-men/

**打开即看，不需要开终端、不需要 Mac 醒着。** 每个交易日美股收盘后由 GitHub Actions
在云端跑完引擎，把结果提交回本仓库，Pages 自动更新页面。

- 想立刻手动跑一次：[Actions → Run workflow](https://github.com/frankfang2025/three-wise-men/actions/workflows/daily.yml)，约 2 分钟
- 机器可读结果：[`docs/data/latest.json`](https://frankfang2025.github.io/three-wise-men/data/latest.json)
- 历次换股就是本仓库的 commit 历史（`每日刷新: SWITCH XXX`）

> **云端与本地并存的注意事项**：仓库跟踪 `data/state.json` 和 `data/history.jsonl`
> （持仓状态与换股记录）。如果本地也在跑每日任务，两边会各自改这两个文件，
> `git pull` 时会冲突。建议二选一：既然云端已接管每日刷新，就关掉本地定时任务
> `launchctl bootout gui/$(id -u)/com.threewisemen.daily`；
> 本地若临时跑过，拉取前先 `git checkout data/` 丢弃本地改动。

---

> **本地部署的位置注意**：本项目必须放在 `~/` 而不是 `~/Documents`。macOS 的 TCC 隐私保护
> 不允许 LaunchAgent 读取 `~/Documents`、`~/Desktop`、`~/Downloads` 里的文件内容
> （实测：能 cd、能 ls、能写，但读文件内容返回 Operation not permitted，
> 定时任务会以退出码 126 静默失败）。搬回去会立刻坏掉。

从 NotebookLM 三本笔记本里把三位的**可量化标准**抽出来，落成一套每天能刷新的筛选引擎。
三位是"**与**"关系——任何一人否决即出局。

## 网页版（常驻，浏览器点一下就跑）

打开 **http://127.0.0.1:8802** —— 页面顶部有「立即刷新」按钮，点一下后台跑引擎
（实时进度日志会展开），约 15 秒跑完自动重载页面显示新结果。
勾选「强制重拉基本面」等同 `--full`。

服务已注册为常驻 LaunchAgent，开机自启、崩溃自动拉起（实测强杀后 launchd 立即重启）。

```bash
launchctl list | grep threewise.web     # 看状态，第一列是 PID
curl -s localhost:8802/api/snapshot     # 拿 JSON 结果，可接别的程序
tail -20 data/web.err                   # 访问日志
```

想让手机/平板也能访问（同一 WiFi）：把 plist 里的 `webapp.py` 后面加一行
`<string>--lan</string>`，重新 bootstrap 即可，届时用 Mac 的局域网 IP 访问。
默认只监听 `127.0.0.1`，不对外暴露。

停掉：`launchctl bootout gui/$(id -u)/com.threewisemen.web`

| 接口 | 用途 |
|---|---|
| `GET /` | 带控制条的仪表盘 |
| `POST /api/refresh?full=0\|1` | 触发一次刷新 |
| `GET /api/status` | 轮询进度（running / log / rc / error） |
| `GET /api/snapshot` | 当前完整快照 JSON |

## 每天怎么用

```bash
./refresh.sh          # 拉实时数据 → 重新打分 → 更新 dashboard.html
python3 status.py     # 只看当前结论，不联网
open dashboard.html   # 看完整仪表盘
```

`./refresh.sh --full` 强制重拉全部基本面（平时基本面缓存 5 天、现金流量表缓存 30 天，
价格和宏观每次都是实时的）。

### 让它自己每天跑（已安装并验证）

定时任务已注册，周一到周六 07:30 本地时间（美股收盘后）自动刷新。

```bash
launchctl list | grep threewise                              # 看状态，第二列是上次退出码
launchctl kickstart gui/$(id -u)/com.threewisemen.daily      # 立刻手动触发一次
tail -20 data/cron.log                                       # 看运行日志
```

改时间：编辑 `com.threewisemen.daily.plist` 里的 `Hour`/`Minute`，然后

```bash
cp com.threewisemen.daily.plist ~/Library/LaunchAgents/
launchctl bootout  gui/$(id -u)/com.threewisemen.daily
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.threewisemen.daily.plist
```

停掉：`launchctl bootout gui/$(id -u)/com.threewisemen.daily`

> 用 `bootstrap`/`bootout`，不要用已废弃的 `load`/`unload` —— 后者在重复注册时
> 会抛 `Load failed: 5: Input/output error`，看起来像失败其实任务已经装上了。

## 跑完怎么找你

`notify.py` 负责交付，三条并行：

| 方式 | 行为 |
|---|---|
| **macOS 通知** | 每次跑完弹一条。`HOLD` 静音；`SWITCH` / `INIT` / `NO_CONSENSUS` 带 Glass 提示音 |
| **镜像副本** | 自动复制一份到 `~/Documents/Phython test/三人共识选股.html`（launchd 能写 Documents，只是不能读） |
| **摘要流水** | `data/digest.log` 一行一次，`grep SWITCH data/digest.log` 可回看历次换股 |

改镜像位置：编辑 `notify.py` 顶部的 `MIRROR_DIR`，设为 `None` 则关闭。

> 如果收不到通知：系统设置 → 通知 → 找到「脚本编辑器」或「osascript」，把通知打开。
> `osascript` 退出码为 0 只代表命令执行了，不代表通知中心一定放行。

## 三套框架从哪来

`frameworks/` 下三个文件由 NotebookLM 检索原始资料后归纳：

| 文件 | 来源笔记本 | 份数 |
|---|---|---|
| `buffett_framework.md` | 巴菲特致股东信 1977–2024 | 255 |
| `dalio_framework.md` | Ray Dalio 原则与债务周期 | 118 |
| `dimon_framework.md` | Jamie Dimon 2025–26 达沃斯发言与股东信 | 165 |

评分里每条门槛都对应其中的原始表述，`scoring.py` 的注释标了依据。

## 否决门（各自原话口径）

**Buffett** — 能力圈外 / ROE<12% / 净负债>3.5×EBITDA / 负债权益比>150%（ROE 靠杠杆而非生意）
/ 股东盈余为负 / 股东盈余收益率打不过 10 年国债 / 实测油价β>0.8（纯大宗价格接受者）
/ 近四年自由现金流为正不足 3 年

**Dimon** — 传统软件、私人信贷、商业地产（他点名警示的三块）/ 净负债>4×EBITDA（达不到堡垒资产负债表）
/ PE>30（他说 23 倍已是"估值区间上限"）

**Dalio** — 既非实物资产又无实测通胀对冲 / 通胀上行期实测通胀β为负 / 货币贬值读数高时的名义债券代理

## 关键设计

**标签 vs 实测**：通胀对冲能力不用主观标签，而是对市场隐含盈亏平衡通胀（TIP/IEF）做周频回归。
微观定价权 ≠ 股价能对冲通胀——可口可乐品牌定价权极强，但实测通胀β是 **−0.49**；
公用事业 NEE 的利率β **−0.094**，本质是"伪装成股票的名义债券"，正是 Dalio 点名要回避的。

**连续加权象限**：增长/通胀轴用 sigmoid 转成置信度再混合四象限得分，
避免 z 值在零点附近时因噪音来回翻象限。任一轴落在中性带内会如实标注"判定不稳"。

**熊陡 vs 牛陡**：长端上行驱动的曲线陡峭是财政/通胀风险溢价，计入通胀轴；
只有短端下行驱动的牛陡才算增长信号。

**换股规则**：在任被任一人否决 → 立即换；挑战者综合分领先 ≥5 分且连续 3 个交易日 → 换；否则持有。
综合分 = `0.45×最低分 + 0.55×均值`，防止"两人极满意、一人勉强"靠平均分蒙混过关。

## 文件

```
universe.py      候选池 93 只 + 主题标注（含 4 个反面样本用于验证否决逻辑）
macro.py         实时宏观状态机（四象限、贬值读数、信用利差警戒）
fundamentals.py  数据层 + 实测因子回归（通胀β/利率β/油价β/金β）+ 现金流持久性
scoring.py       三人独立打分与否决
run_daily.py     每日编排 + 换股规则 + 落盘
render.py        自包含 HTML 仪表盘
status.py        命令行快速查看
data/            latest.json / history.jsonl / state.json / 缓存
```

## 两个已修的隐患（别改回去）

**解释器绝对路径**：`refresh.sh` 写死 `/opt/homebrew/bin/python3`。launchd 的 PATH 只有
`/usr/bin:/bin:/usr/sbin:/sbin`，`/usr/bin/env python3` 会落到
`/Library/Developer/CommandLineTools/usr/bin/python3`——那个解释器没有 yfinance，
定时任务会每天静默崩掉。

**下载重试 + 缓存隔离**：yfinance 批量下载在多线程下常因 sqlite 时区缓存争用丢票
（实测一次丢 12 只）。`yfsetup.py` 把缓存隔离到 `data/yf_cache`，
`load_prices()` 会逐个补拉缺失标的；补不回来的直接排除出候选，
不让降级数据混进评分。

## 局限

① 主题标签（实物资产强度、Dimon 主题归属）仍是人工判断；
② 保险公司自由现金流含浮存金流入，股东盈余口径偏高；
③ ROIC 用市值/市净率反推股东权益，为代理指标；
④ 利息保障倍数未逐一取数，以净负债/EBITDA 与负债权益比替代；
⑤ 数据源 Yahoo Finance，全部为真实市场数据、无估读；
⑥ **本工具是框架推演，不构成投资建议。**
