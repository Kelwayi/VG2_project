import subprocess
import time

import psutil
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)


def cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return round(int(f.read()) / 1000, 1)
    except OSError:
        return None


def service_active(name):
    try:
        out = subprocess.run(
            ["systemctl", "is-active", name],
            capture_output=True, text=True, timeout=2,
        )
        return out.stdout.strip() == "active"
    except Exception:
        return False


@app.route("/api/stats")
def stats():
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return jsonify(
        cpu=psutil.cpu_percent(interval=0.3),
        temp=cpu_temp(),
        ram=mem.percent,
        ram_used=round(mem.used / 1024**2),
        ram_total=round(mem.total / 1024**2),
        disk=disk.percent,
        disk_used=round(disk.used / 1024**3, 1),
        disk_total=round(disk.total / 1024**3, 1),
        load=[round(x, 2) for x in psutil.getloadavg()],
        uptime=int(time.time() - psutil.boot_time()),
        services={
            "mariadb": service_active("mariadb"),
            "tailscale": service_active("tailscaled"),
            "ufw": service_active("ufw"),
        },
    )


PAGE = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pi status</title>
<style>
  body { font-family: system-ui, sans-serif; background: #111; color: #eee;
         margin: 0; padding: 1.5rem; }
  h1 { margin-top: 0; }
  .grid { display: grid; gap: 1rem;
          grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }
  .card { background: #1e1e1e; border-radius: 10px; padding: 1rem; }
  .label { color: #999; font-size: .85rem; }
  .value { font-size: 1.8rem; margin: .3rem 0; }
  .bar { background: #333; height: 8px; border-radius: 4px; overflow: hidden; }
  .fill { height: 100%; background: #4caf50; width: 0; transition: width .4s; }
  .warn { background: #ff9800; } .bad { background: #f44336; }
  .dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%;
         margin-right: .4rem; background: #f44336; }
  .dot.on { background: #4caf50; }
</style>
</head>
<body>
<h1>Pi status</h1>
<div class="grid">
  <div class="card"><div class="label">CPU</div>
    <div class="value" id="cpu">-</div><div class="bar"><div class="fill" id="cpu-bar"></div></div></div>
  <div class="card"><div class="label">Temperature</div>
    <div class="value" id="temp">-</div><div class="bar"><div class="fill" id="temp-bar"></div></div></div>
  <div class="card"><div class="label">RAM</div>
    <div class="value" id="ram">-</div><div class="bar"><div class="fill" id="ram-bar"></div></div>
    <div class="label" id="ram-detail"></div></div>
  <div class="card"><div class="label">Disk</div>
    <div class="value" id="disk">-</div><div class="bar"><div class="fill" id="disk-bar"></div></div>
    <div class="label" id="disk-detail"></div></div>
  <div class="card"><div class="label">Load (1 / 5 / 15 min)</div>
    <div class="value" id="load">-</div></div>
  <div class="card"><div class="label">Uptime</div>
    <div class="value" id="uptime">-</div></div>
  <div class="card"><div class="label">Services</div><div id="services"></div></div>
</div>
<script>
function setBar(id, pct) {
  const el = document.getElementById(id);
  el.style.width = Math.min(pct, 100) + "%";
  el.className = "fill" + (pct > 90 ? " bad" : pct > 75 ? " warn" : "");
}
function fmtUptime(s) {
  const d = Math.floor(s / 86400), h = Math.floor(s % 86400 / 3600),
        m = Math.floor(s % 3600 / 60);
  return (d ? d + "d " : "") + h + "h " + m + "m";
}
async function update() {
  try {
    const r = await (await fetch("/api/stats")).json();
    cpu.textContent = r.cpu + " %";           setBar("cpu-bar", r.cpu);
    temp.textContent = r.temp === null ? "n/a" : r.temp + " °C";
    setBar("temp-bar", r.temp || 0);
    ram.textContent = r.ram + " %";           setBar("ram-bar", r.ram);
    document.getElementById("ram-detail").textContent =
      r.ram_used + " / " + r.ram_total + " MB";
    disk.textContent = r.disk + " %";         setBar("disk-bar", r.disk);
    document.getElementById("disk-detail").textContent =
      r.disk_used + " / " + r.disk_total + " GB";
    load.textContent = r.load.join(" / ");
    uptime.textContent = fmtUptime(r.uptime);
    services.innerHTML = Object.entries(r.services).map(([n, on]) =>
      '<div><span class="dot' + (on ? " on" : "") + '"></span>' + n + "</div>"
    ).join("");
  } catch (e) { console.error(e); }
}
update();
setInterval(update, 2000);
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(PAGE)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
