"""Generate a static v4 visual mockup for CTOA EK Helper.

This is not the OTClient validator. It is a design-only artifact for deciding
the layout before rewriting Lua widgets.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "runtime" / "otclient_ui_preview"
OUT_HTML = OUT_DIR / "ctoa_helper_mockup_v4.html"


HTML = r"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>CTOA EK Helper Mockup v4</title>
<style>
:root {
  --bg: #303030;
  --bg2: #252525;
  --panel: rgba(26, 26, 26, .52);
  --line: #565656;
  --line-strong: #8d7648;
  --gold: #d7b36a;
  --text: #dedede;
  --muted: #a8a8a8;
  --green: #8fd17f;
  --red: #cf7f7f;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  min-height: 100vh;
  display: grid;
  place-items: center;
  background:
    radial-gradient(circle at 30% 15%, rgba(215,179,106,.12), transparent 28%),
    linear-gradient(135deg, #222, #171717);
  font-family: Verdana, Geneva, sans-serif;
  color: var(--text);
}
.window {
  width: 590px;
  height: 430px;
  background:
    repeating-linear-gradient(135deg, rgba(255,255,255,.025) 0 1px, transparent 1px 5px),
    var(--bg);
  border: 2px solid #5b5b5b;
  box-shadow: inset 0 0 0 1px #181818, 0 20px 60px rgba(0,0,0,.55);
  position: relative;
}
.titlebar {
  height: 24px;
  line-height: 23px;
  text-align: center;
  background: #252525;
  border-bottom: 1px solid #171717;
  font-size: 11px;
  font-weight: 700;
  color: #f1f1f1;
  text-shadow: 1px 1px #000;
}
.body {
  display: grid;
  grid-template-columns: 158px 1fr;
  gap: 24px;
  padding: 36px 34px 26px 34px;
}
.sidebar-title {
  color: var(--gold);
  font-weight: 700;
  font-size: 12px;
  margin-bottom: 5px;
}
.sidebar-sub {
  color: var(--muted);
  font-weight: 700;
  font-size: 11px;
  margin-bottom: 24px;
}
.nav {
  display: grid;
  gap: 9px;
  margin-bottom: 28px;
}
.nav button {
  height: 33px;
  background: rgba(28,28,28,.35);
  border: 1px solid #505050;
  color: var(--muted);
  font-weight: 700;
  font-size: 10px;
}
.nav button.active {
  border-color: var(--line-strong);
  color: var(--gold);
  background: rgba(92,72,32,.24);
}
.side-label {
  color: var(--muted);
  font-size: 11px;
  font-weight: 700;
  margin-bottom: 8px;
}
.profile-pill {
  height: 22px;
  line-height: 22px;
  padding: 0 8px;
  background: var(--bg2);
  border: 1px solid #444;
  font-size: 11px;
  font-weight: 700;
  margin-bottom: 28px;
}
.side-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 24px;
  font-size: 11px;
  font-weight: 700;
  color: var(--text);
}
.status-dot {
  color: var(--green);
}
.hint {
  margin-top: 26px;
  font-size: 11px;
  color: var(--muted);
  font-weight: 700;
}
.content-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  border-bottom: 1px solid var(--line-strong);
  padding-bottom: 8px;
  margin-bottom: 16px;
}
.content-title {
  color: var(--gold);
  font-size: 12px;
  font-weight: 700;
}
.content-meta {
  color: var(--muted);
  font-size: 10px;
  font-weight: 700;
}
.settings {
  display: grid;
  gap: 8px;
}
.setting-row {
  display: grid;
  grid-template-columns: 1fr 76px;
  align-items: center;
  min-height: 29px;
  padding: 0 10px;
  background: var(--panel);
  border: 1px solid #484848;
  box-shadow: inset 0 0 0 1px rgba(0,0,0,.25);
}
.setting-row.strong {
  border-color: #5f8057;
  background: rgba(31, 52, 31, .56);
}
.setting-name {
  font-size: 11px;
  font-weight: 700;
  color: var(--text);
}
.setting-value {
  text-align: right;
  font-size: 11px;
  font-weight: 700;
  color: var(--green);
}
.setting-value.off {
  color: var(--red);
}
.note {
  margin-top: 14px;
  color: var(--muted);
  font-size: 11px;
  font-weight: 700;
  line-height: 1.6;
}
.footer {
  position: absolute;
  right: 22px;
  bottom: 16px;
}
.close {
  width: 76px;
  height: 30px;
  border: 1px solid #555;
  background: rgba(30,30,30,.55);
  color: var(--muted);
  font-size: 10px;
  font-weight: 700;
}
</style>
</head>
<body>
  <div class="window">
    <div class="titlebar">CTOA EK Helper Options</div>
    <div class="body">
      <aside>
        <div class="sidebar-title">CTOA EK</div>
        <div class="sidebar-sub">native helper</div>
        <nav class="nav">
          <button>Healing</button>
          <button class="active">Tools</button>
        </nav>
        <div class="side-label">Active profile</div>
        <div class="profile-pill">EK monk profile</div>
        <div class="side-row"><span>Enabled</span><span class="status-dot">ON</span></div>
        <div class="side-row"><span>Status</span><span class="status-dot">Ready</span></div>
        <div class="hint">Ctrl+H opens panel</div>
      </aside>

      <main>
        <div class="content-head">
          <div class="content-title">Combat Tools</div>
          <div class="content-meta">smart EK mode</div>
        </div>
        <div class="settings">
          <div class="setting-row"><div class="setting-name">Auto Haste</div><div class="setting-value off">OFF</div></div>
          <div class="setting-row strong"><div class="setting-name">Spell Rotation</div><div class="setting-value">ON</div></div>
          <div class="setting-row"><div class="setting-name">AoE min mobs</div><div class="setting-value">2</div></div>
          <div class="setting-row"><div class="setting-name">Exori Gran min</div><div class="setting-value">3</div></div>
          <div class="setting-row"><div class="setting-name">Single target fallback</div><div class="setting-value">ICO</div></div>
          <div class="setting-row strong"><div class="setting-name">Auto Exeta</div><div class="setting-value">ON</div></div>
          <div class="setting-row"><div class="setting-name">Visible mobs for exeta</div><div class="setting-value">2</div></div>
        </div>
        <div class="note">Monsters: nearby 0 / visible 2</div>
      </main>
    </div>
    <div class="footer"><button class="close">Close</button></div>
  </div>
</body>
</html>
"""


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(HTML, encoding="utf-8")
    print(f"mockup: {OUT_HTML}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
