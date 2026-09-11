# -*- coding: utf-8 -*-
"""网页版：浏览器点一下，后台跑引擎，跑完自动刷新页面。

  python3 webapp.py              只监听本机  http://127.0.0.1:8802
  python3 webapp.py --lan        同时监听局域网（手机/平板可访问）
  python3 webapp.py --port 9000  换端口
"""
import os, sys, json, threading, subprocess, datetime as dt
from flask import Flask, Response, jsonify, send_from_directory

HERE = os.path.dirname(os.path.abspath(__file__))
DASH = os.path.join(HERE, "dashboard.html")
LATEST = os.path.join(HERE, "data", "latest.json")
PY = "/opt/homebrew/bin/python3" if os.path.exists("/opt/homebrew/bin/python3") else sys.executable

app = Flask(__name__)
JOB = {"running": False, "log": [], "started": None, "finished": None,
       "error": None, "rc": None}
_lock = threading.Lock()


def _worker(full: bool):
    try:
        cmd = [PY, "run_daily.py"] + (["--full"] if full else [])
        p = subprocess.Popen(cmd, cwd=HERE, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in p.stdout:
            line = line.rstrip()
            if line and not line.startswith("[") and "Warning" not in line:
                JOB["log"].append(line)
                del JOB["log"][:-40]          # 只留最近 40 行
        p.wait()
        JOB["rc"] = p.returncode
        if p.returncode != 0:
            JOB["error"] = f"引擎退出码 {p.returncode}"
    except Exception as e:
        JOB["error"] = str(e)
    finally:
        JOB["running"] = False
        JOB["finished"] = dt.datetime.now().isoformat(timespec="seconds")


CONTROL = """
<div id="ctl" style="position:sticky;top:0;z-index:99;background:var(--panel);
 border:1px solid var(--line);border-radius:11px;padding:12px 16px;margin-bottom:16px;
 display:flex;align-items:center;gap:14px;flex-wrap:wrap;
 box-shadow:0 2px 14px rgba(0,0,0,.18)">
  <button id="go" style="background:var(--acc);color:#0d1117;border:0;border-radius:8px;
   padding:9px 20px;font-size:13.5px;font-weight:700;cursor:pointer">立即刷新</button>
  <label style="font-size:12px;color:var(--dim);display:flex;align-items:center;gap:5px;cursor:pointer">
    <input type="checkbox" id="full"> 强制重拉基本面（较慢）</label>
  <span id="msg" style="font-size:12.5px;color:var(--dim)"></span>
  <span style="flex:1"></span>
  <span id="stamp" style="font-size:11.5px;color:var(--dim)"></span>
</div>
<pre id="log" style="display:none;background:var(--panel2);border:1px solid var(--line);
 border-radius:9px;padding:12px 14px;font-size:11.5px;line-height:1.6;color:var(--dim);
 max-height:210px;overflow:auto;margin:-6px 0 16px;white-space:pre-wrap"></pre>
<script>
const $=id=>document.getElementById(id);
let timer=null;
function paint(s){
  $('go').disabled=s.running;
  $('go').style.opacity=s.running?.55:1;
  $('go').textContent=s.running?'正在跑…':'立即刷新';
  $('msg').textContent=s.running?'实时拉取价格与宏观，重新打分（约 15 秒）'
      :(s.error?('✗ '+s.error):(s.finished?'✓ 完成于 '+s.finished.slice(11,16):''));
  $('msg').style.color=s.error?'var(--bad)':'var(--dim)';
  if(s.log&&s.log.length){$('log').style.display='block';$('log').textContent=s.log.join('\\n');
    $('log').scrollTop=$('log').scrollHeight;}
}
async function poll(){
  const s=await (await fetch('/api/status')).json();
  paint(s);
  if(!s.running){clearInterval(timer);timer=null;
    if(!s.error){$('msg').textContent='✓ 完成，正在载入新结果…';setTimeout(()=>location.reload(),700);}}
}
$('go').onclick=async()=>{
  $('log').textContent='';
  await fetch('/api/refresh?full='+($('full').checked?'1':'0'),{method:'POST'});
  if(!timer)timer=setInterval(poll,900);
  poll();
};
fetch('/api/status').then(r=>r.json()).then(s=>{
  paint(s); if(s.running&&!timer)timer=setInterval(poll,900);});
</script>
"""


@app.get("/")
def index():
    if not os.path.exists(DASH):
        return ("<h2 style='font-family:system-ui;padding:40px'>还没有生成过报告。"
                "先在终端跑一次 <code>./refresh.sh</code>，或直接点刷新。</h2>" + CONTROL)
    html = open(DASH).read()
    stamp = ""
    if os.path.exists(LATEST):
        try:
            d = json.load(open(LATEST))
            stamp = f"数据刷新于 {d['run_at'][:16].replace('T',' ')} · 当前 {d['pick'] or '空仓'}"
        except Exception:
            pass
    # 把控制条插进 .wrap 开头，保持 dashboard.html 本身干净（镜像副本仍是纯静态页）
    html = html.replace('<div class="wrap">', '<div class="wrap">' + CONTROL, 1)
    html = html.replace('<span id="stamp" style="font-size:11.5px;color:var(--dim)"></span>',
                        f'<span id="stamp" style="font-size:11.5px;color:var(--dim)">{stamp}</span>', 1)
    return Response(html, mimetype="text/html")


@app.post("/api/refresh")
def refresh():
    from flask import request
    with _lock:
        if JOB["running"]:
            return jsonify(ok=False, msg="已有任务在跑"), 409
        JOB.update(running=True, log=[], error=None, rc=None,
                   started=dt.datetime.now().isoformat(timespec="seconds"), finished=None)
    threading.Thread(target=_worker, args=(request.args.get("full") == "1",),
                     daemon=True).start()
    return jsonify(ok=True)


@app.get("/api/status")
def status():
    return jsonify(JOB)


@app.get("/api/snapshot")
def snapshot():
    if not os.path.exists(LATEST):
        return jsonify(error="尚无快照"), 404
    return send_from_directory(os.path.join(HERE, "data"), "latest.json")


if __name__ == "__main__":
    port = 8802
    if "--port" in sys.argv:
        port = int(sys.argv[sys.argv.index("--port") + 1])
    host = "0.0.0.0" if "--lan" in sys.argv else "127.0.0.1"
    print(f"\n  三人共识选股 · 网页版")
    print(f"  → http://127.0.0.1:{port}")
    if host == "0.0.0.0":
        import socket
        try:
            ip = socket.gethostbyname(socket.gethostname())
            print(f"  → http://{ip}:{port}   (局域网，手机可访问)")
        except Exception:
            pass
    print()
    app.run(host=host, port=port, debug=False, threaded=True)
