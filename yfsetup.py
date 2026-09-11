# -*- coding: utf-8 -*-
"""yfinance 全局设置。必须在任何 yf 调用前 import。

默认时区缓存在 ~/Library/Caches/py-yfinance，多进程/多线程并发时会出现
OperationalError('unable to open database file')。改到项目内独占一份，
既避免与本机其他 yfinance 程序争用，也保证 launchd 下可写。
"""
import os
import yfinance as yf

_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "yf_cache")
os.makedirs(_CACHE, exist_ok=True)
try:
    yf.set_tz_cache_location(_CACHE)
except Exception:
    pass
