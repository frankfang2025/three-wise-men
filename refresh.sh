#!/bin/bash
# 每日刷新。用法: ./refresh.sh   (加 --full 强制重拉全部基本面)
# 注意: launchd 的 PATH 极简，必须写死解释器绝对路径，否则会落到没装 yfinance 的
#       /Library/Developer/CommandLineTools/usr/bin/python3 上静默失败。
cd "$(dirname "$0")" || exit 1

PY=/opt/homebrew/bin/python3
[ -x "$PY" ] || PY="$(command -v python3)"
[ -x "$PY" ] || { echo "[$(date)] 找不到 python3"; exit 1; }

echo "[$(date '+%F %T')] 开始刷新 (解释器 $PY)"
"$PY" run_daily.py "$@"
rc=$?
echo "[$(date '+%F %T')] 结束，退出码 $rc"
exit $rc
