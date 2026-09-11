# -*- coding: utf-8 -*-
"""跑完之后把结论送到你面前，而不是静默覆盖一个文件。

  1) macOS 通知  —— 换股/被否决时带声音，HOLD 时静音
  2) 镜像副本    —— 复制一份 dashboard.html 到你习惯翻的目录
  3) 摘要流水    —— data/digest.log 一行一天，方便 grep 回看
"""
import os, sys, subprocess, shutil, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))

# 想让副本落在别处就改这里；设为 None 关闭镜像
MIRROR_DIR = "/Users/yingjiefang/Documents/Phython test"


IS_MAC = sys.platform == "darwin"


def _osa(title, subtitle, body, sound=None):
    """用 osascript 发通知。正文里的双引号和反斜杠要转义，否则 AppleScript 会语法错。
    非 macOS（如 GitHub Actions 的 Linux runner）直接跳过。"""
    if not IS_MAC:
        return
    def esc(s):
        return str(s).replace("\\", "\\\\").replace('"', '\\"')
    script = (f'display notification "{esc(body)}" '
              f'with title "{esc(title)}" subtitle "{esc(subtitle)}"')
    if sound:
        script += f' sound name "{esc(sound)}"'
    try:
        subprocess.run(["/usr/bin/osascript", "-e", script],
                       check=False, capture_output=True, timeout=15)
    except Exception:
        pass


def deliver(snap, dashboard_path, verbose=True):
    pick, action, reason = snap["pick"], snap["action"], snap["reason"]
    P = next((r for r in snap["ranked"] if r["ticker"] == pick), None)
    changed = action in ("SWITCH", "INIT", "NO_CONSENSUS")

    # ---- 1) 通知 ----
    if P:
        m = P["metrics"]
        title = {"SWITCH": f"⚠️ 换股 → {pick}", "INIT": f"建仓 {pick}",
                 "NO_CONSENSUS": "⚠️ 无共识标的，空仓"}.get(action, f"{pick} 继续持有")
        sub = (f"综合 {P['composite']} · 巴 {P['buffett']['score']:.0f} / "
               f"D {P['dimon']['score']:.0f} / R {P['dalio']['score']:.0f}")
        body = (f"${P['price']:.2f} · PE {m['trailing_pe']:.1f}x · "
                f"股东盈余率 {m['fcf_yield']:.2%} vs 10Y {snap['macro']['ten_year']:.2f}%")
    else:
        title, sub, body = "⚠️ 无共识标的，空仓", reason[:60], ""
    _osa(title, sub, body, sound="Glass" if changed else None)

    # ---- 2) 镜像副本 ----
    mirrored = None
    if MIRROR_DIR and os.path.isdir(MIRROR_DIR):
        try:
            dst = os.path.join(MIRROR_DIR, "三人共识选股.html")
            shutil.copyfile(dashboard_path, dst)
            mirrored = dst
        except Exception as e:
            if verbose:
                print(f"  镜像副本失败: {e}")

    # ---- 3) 摘要流水 ----
    line = (f"{snap['date']} {snap['run_at'][11:16]}  [{action:12s}] {pick or '空仓':6s} "
            f"综合 {P['composite'] if P else 0:5.1f}  "
            f"通过 {sum(1 for r in snap['ranked'] if r['consensus'])}/{len(snap['ranked'])}  "
            f"{snap['macro']['quadrant'].split('（')[0]}  |  {reason}")
    with open(os.path.join(HERE, "data", "digest.log"), "a") as f:
        f.write(line + "\n")

    if verbose:
        print(f"  已通知: {title}")
        if mirrored:
            print(f"  镜像副本: {mirrored}")
    return mirrored
