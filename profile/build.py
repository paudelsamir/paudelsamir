#!/usr/bin/env python3
"""Builds the GitHub profile: one rich SVG row per project — big display
name, the author's own one-liner, and a small looped scene of what it
does — grouped under pill badges, stacked into README.md with each row
linked to its repo.

GitHub shows README images as plain <img>: no scripts, no webfonts. CSS
@keyframes still run, so every scene carries one looped motion, with both
fonts embedded as base64 WOFF subsets. Backgrounds stay transparent so
rows sit on GitHub's own page colour; every row ships in light and dark,
picked by <picture>.

  python3 profile/build.py        # GITHUB_TOKEN optional, else data.json

.github/workflows/profile.yml reruns this daily so the counts stay live.
"""

import base64
import io
import json
import os
import re
import sys
import urllib.request
from html import escape as hesc

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
USER = "paudelsamir"
ACCENT = "#29a298"
W = 880
PAD = 28

INTER_EB = "/home/sam/.local/share/fonts/inter/Inter-ExtraBold.ttf"
JB_REG = "/usr/share/fonts/TTF/JetBrainsMonoNerdFont-Regular.ttf"
JB_BOLD = "/usr/share/fonts/TTF/JetBrainsMonoNerdFont-Bold.ttf"

THEMES = {
    "light": {"fg": "#191817", "hair": "rgba(25,24,23,.16)"},
    "dark": {"fg": "#eae7de", "hair": "rgba(234,231,222,.16)"},
}

# ---------------------------------------------------------------- data ---

def api(path):
    req = urllib.request.Request(
        f"https://api.github.com/{path}",
        headers={"User-Agent": USER, "Accept": "application/vnd.github+json",
                 **({"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"}
                    if os.environ.get("GITHUB_TOKEN") else {})},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def fetch_data():
    user = api(f"users/{USER}")
    repos, page = [], 1
    while True:
        batch = api(f"users/{USER}/repos?per_page=100&type=owner&page={page}")
        repos += batch
        if len(batch) < 100:
            break
        page += 1
    own = [r for r in repos if not r["fork"]]
    flag = next(r for r in own if r["name"] == "365DaysOfData")
    return {
        "repos": user["public_repos"],
        "stars": sum(r["stargazers_count"] for r in own),
        "followers": user["followers"],
        "flag_stars": flag["stargazers_count"],
        "flag_forks": flag["forks_count"],
    }


DATA_JSON = os.path.join(HERE, "data.json")
try:
    data = fetch_data()
    with open(DATA_JSON, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
except Exception as e:  # offline / rate-limited: reuse last good numbers
    print(f"GitHub API unavailable ({e}), using data.json", file=sys.stderr)
    with open(DATA_JSON) as f:
        data = json.load(f)

# ---------------------------------------------------------------- fonts --

FONTS = {}


def load_font(path):
    from fontTools.ttLib import TTFont
    font = TTFont(path)
    return font, font["head"].unitsPerEm, font["hmtx"], font.getBestCmap()


for _key, _path in (("disp", INTER_EB), ("mono", JB_REG), ("bold", JB_BOLD)):
    if os.path.exists(_path):
        FONTS[_key] = load_font(_path)
    else:
        print(f"missing font {_path}, falling back to system stack", file=sys.stderr)


def adv(ch, key, size):
    if key not in FONTS:
        return size * 0.6
    _font, upm, hmtx, cmap = FONTS[key]
    glyph = cmap.get(ord(ch), cmap.get(ord(" "), ".notdef"))
    try:
        w = hmtx[glyph][0]
    except KeyError:
        w = hmtx[cmap.get(ord(" "))][0]
    return w / upm * size


def text_w(s, key, size):
    return sum(adv(c, key, size) for c in s)


def trunc(s, key, size, width):
    if text_w(s, key, size) <= width:
        return s
    while s and text_w(s + "…", key, size) > width:
        s = s[:-1]
    return s + "…"


def wrap(text, key, size, width):
    words, lines, cur = text.split(" "), [], ""
    for wd in words:
        trial = f"{cur} {wd}".strip()
        if text_w(trial, key, size) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


USED = {}
_CUR = None


def T(card, s, key="mono"):
    USED.setdefault(card, {}).setdefault(key, set()).update(s)
    return hesc(s)


def S(s, key="mono"):
    """Scene text, recorded under the row currently being built."""
    return T(_CUR, s, key)


def subset_b64(path, chars):
    from fontTools import subset
    from fontTools.ttLib import TTFont
    opts = subset.Options()
    opts.flavor = "woff"
    font = TTFont(path)
    ss = subset.Subsetter(opts)
    ss.populate(text="".join(sorted(chars)))
    ss.subset(font)
    buf = io.BytesIO()
    font.save(buf)
    return base64.b64encode(buf.getvalue()).decode()


def font_css(card):
    if not FONTS:
        return ""
    out = []
    for key, fam in (("disp", "D"), ("mono", "M"), ("bold", "B")):
        path = {"disp": INTER_EB, "mono": JB_REG, "bold": JB_BOLD}[key]
        chars = USED.get(card, {}).get(key)
        if not chars or not os.path.exists(path):
            continue
        out.append(
            f"@font-face{{font-family:{fam};src:url(data:font/woff;base64,"
            f"{subset_b64(path, chars)}) format('woff')}}"
        )
    return "".join(out)


# ---------------------------------------------------------------- svg ----

MOTION_OFF = "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"


def svg(card, theme, h, css, body, label, w=W):
    t = THEMES[theme]
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}" role="img" aria-label="{hesc(label)}">'
        f"<title>{hesc(label)}</title><style>"
        f"{font_css(card)}"
        f".m{{font-family:M,ui-monospace,SFMono-Regular,monospace;font-size:11px;fill:{t['fg']}}}"
        f".d{{font-family:D,Inter,system-ui,sans-serif;font-weight:800;fill:{t['fg']}}}"
        f".b{{font-family:B,ui-monospace,monospace;font-weight:700;fill:{t['fg']}}}"
        f".dim{{fill-opacity:.55}}.acc{{fill:{ACCENT}}}"
        f".hair{{stroke:{t['hair']};stroke-width:1}}"
        f".ln{{fill:none;stroke:{t['fg']};stroke-opacity:.5}}"
        f".fill{{fill:{t['fg']}}}"
        f".ar{{fill:none;stroke:{ACCENT};stroke-width:1.7;stroke-linecap:round;stroke-linejoin:round}}"
        f"{css}{MOTION_OFF}</style>{body}</svg>"
    )


def arrow(x, y, s=8):
    return (
        f'<path class="ar" d="M{x},{y + s}L{x + s},{y}'
        f"M{x + s * .32},{y}H{x + s}V{y + s * .68}\"/>"
    )


def pct(i, n):
    return f"{i / n * 100:.2f}%"


def appear(cid, on, off=0.9, dur=8):
    return (f"@keyframes {cid}{{0%,{pct(max(0, on - 0.001), 1)}{{opacity:0}}"
            f"{pct(on, 1)},{pct(off, 1)}{{opacity:1}}"
            f"{pct(min(1, off + 0.04), 1)},100%{{opacity:0}}"
            f"}}.{cid}{{animation:{cid} {dur}s linear infinite}}\n")


BLINK = "@keyframes bl{0%,49%{opacity:1}50%,100%{opacity:0}}.bl{animation:bl 1.1s steps(1) infinite}\n"

# --------------------------------------------------------------- header --


def header(theme):
    tag = "I turn data into things that run."
    tw = text_w(tag, "mono", 11.5)
    body = (
        f'<text class="d" x="{PAD - 2}" y="58" font-size="30">{T("header", "SAMIR PAUDEL", "disp")}</text>'
        f'<text class="m dim" x="{PAD}" y="78" font-size="11.5">{T("header", tag)}</text>'
        f'<rect class="bl" x="{PAD + tw + 7}" y="67" width="7.5" height="13" fill="{ACCENT}"/>'
    )
    return svg("header", theme, 90, BLINK, body,
               f"Samir Paudel. {tag}")


# --------------------------------------------------------- section pill ---


def monitor(inner=""):
    return (f'<rect class="ln" x=".5" y=".5" width="199" height="103" rx="6"/>{inner}')


def bars(_t, hs=(34, 58, 44, 72, 52), hi=3, dur=7):
    rects, css = "", ""
    for i, h in enumerate(hs):
        x = 30 + i * 30
        y = 92 - h
        cls = f"b{i}"
        css += (f"@keyframes {cls}{{0%,{pct(0.06 + i * 0.07, 1)}{{transform:scaleY(.04)}}"
                f"{pct(0.2 + i * 0.07, 1)},88%{{transform:scaleY(1)}}96%,100%{{transform:scaleY(.04)}}}}"
                f".{cls}{{transform-box:fill-box;transform-origin:50% 100%;animation:{cls} {dur}s ease-in-out infinite}}\n")
        fill = ACCENT if i == hi else _t["fg"]
        op = "" if i == hi else ' fill-opacity=".35"'
        rects += f'<rect class="{cls}" x="{x}" y="{y}" width="18" height="{h}" rx="3" fill="{fill}"{op}/>'
    return css, monitor(rects)


def branch(_t):
    css = ("@keyframes sw{0%,44%{opacity:1}50%,94%{opacity:.25}100%{opacity:1}}"
           "@keyframes sw2{0%,44%{opacity:.25}50%,94%{opacity:1}100%{opacity:.25}}"
           ".sw{animation:sw 6s ease-in-out infinite}.sw2{animation:sw2 6s ease-in-out infinite}\n")
    body = monitor(
        f'<circle cx="26" cy="60" r="6" fill="{ACCENT}"/>'
        f'<path class="ln sw" d="M36,60 C70,60 70,38 120,38"/><circle class="fill sw" cx="126" cy="38" r="4"/>'
        f'<path class="ln sw2" d="M36,60 C70,60 70,80 120,80"/><circle class="fill sw2" cx="126" cy="80" r="4"/>'
        f'<rect class="fill" x="140" y="33" width="44" height="4" fill-opacity=".3"/>'
        f'<rect class="fill" x="140" y="75" width="30" height="4" fill-opacity=".3"/>')
    return css, body


def wave(_t):
    css = ("@keyframes wv{0%,100%{transform:scaleY(.25)}50%{transform:scaleY(1)}}"
           ".wv{transform-box:fill-box;transform-origin:50% 50%;animation:wv 1s ease-in-out infinite}\n")
    bars_ = "".join(
        f'<rect class="wv" x="{52 + k * 13}" y="40" width="6" height="26" rx="3" fill="{ACCENT}" '
        f'style="animation-delay:-{k * 0.12:.2f}s"/>' for k in range(7))
    body = monitor(
        f'{bars_}<circle class="ln" cx="158" cy="53" r="11"/>'
        f'<rect x="156" y="47" width="4" height="9" rx="2" fill="{ACCENT}"/>')
    return css, body


def gauge(_t):
    import math

    def arc(cx, cy, r, a0, a1, steps=24):
        pts = [f"{cx + r * math.cos(a0 + (a1 - a0) * k / steps):.1f},"
               f"{cy + r * math.sin(a0 + (a1 - a0) * k / steps):.1f}"
               for k in range(steps + 1)]
        return "M" + " L".join(pts)

    css = ("@keyframes nd2{0%,100%{transform:rotate(-44deg)}50%{transform:rotate(40deg)}}"
           ".nd2{transform-box:fill-box;transform-origin:50% 100%;animation:nd2 5s ease-in-out infinite}\n")
    ticks = "".join(
        f'<line class="ln" x1="{100 + 58 * math.cos(math.pi + f * math.pi):.1f}" '
        f'y1="{88 + 58 * math.sin(math.pi + f * math.pi):.1f}" '
        f'x2="{100 + 49 * math.cos(math.pi + f * math.pi):.1f}" '
        f'y2="{88 + 49 * math.sin(math.pi + f * math.pi):.1f}"/>'
        for f in (0, 0.25, 0.5, 0.75, 1))
    body = monitor(
        f'<path d="{arc(100, 88, 58, math.pi, 2 * math.pi)}" class="ln"/>{ticks}'
        f'<path d="{arc(100, 88, 58, math.pi, math.pi + 0.92 * math.pi)}" fill="none" '
        f'stroke="{ACCENT}" stroke-width="3" stroke-linecap="round"/>'
        f'<g class="nd2"><line x1="100" y1="88" x2="100" y2="44" stroke="{ACCENT}" '
        f'stroke-width="2.5" stroke-linecap="round"/></g>'
        f'<circle cx="100" cy="88" r="5" fill="none" stroke="{_t["fg"]}" stroke-opacity=".6"/>'
        f'<circle cx="100" cy="88" r="1.8" fill="{ACCENT}"/>')
    return css, body


def chart(_t):
    css = ("@keyframes dr{0%,12%{stroke-dashoffset:1}55%,85%{stroke-dashoffset:0}96%,100%{stroke-dashoffset:1}}"
           ".dr{animation:dr 8s ease-in-out infinite}"
           + appear("hd", 0.5, 0.9, 8))
    body = monitor(
        f'<line class="hair" x1="14" y1="90" x2="186" y2="90"/>'
        f'<path class="dr" d="M20,82 L52,72 L84,76 L116,56 L148,60 L180,32" pathLength="1" '
        f'stroke-dasharray="1" fill="none" stroke="{ACCENT}" stroke-width="2.5" stroke-linecap="round"/>'
        f'<circle class="hd" cx="180" cy="32" r="4" fill="{ACCENT}" opacity="0"/>')
    return css, body


def scan(_t):
    dots = "".join(
        f'<circle class="fill" cx="{40 + c * 16}" cy="{30 + r * 14}" r="1.6" fill-opacity=".3"/>'
        for r in range(5) for c in range(8))
    css = ("@keyframes sc{0%,100%{transform:translate(0)}50%{transform:translate(120px)}}"
           ".sc{animation:sc 5s ease-in-out infinite}\n")
    body = monitor(
        f'{dots}<rect class="sc" x="36" y="24" width="2.5" height="76" fill="{ACCENT}"/>'
        f'<rect x="96" y="44" width="34" height="26" fill="none" stroke="{ACCENT}" stroke-width="1.5"/>')
    return css, body


def grid(_t):
    css, body = "", monitor("")
    for k in range(48):
        c, r_ = divmod(k, 4)
        cid = f"g{k % 4}"
        if k < 4:
            css += (f"@keyframes {cid}{{0%,{pct(0.05 + k * 0.18, 1)}{{opacity:.15}}"
                    f"{pct(0.16 + k * 0.18, 1)},88%{{opacity:1}}96%,100%{{opacity:.15}}}}"
                    f".{cid}{{animation:{cid} 9s linear infinite}}\n")
        on = (k % 3) != 0
        op = "" if on else ' fill-opacity=".3"'
        body += (f'<rect class="{cid}" x="{30 + c * 12}" y="{30 + r_ * 12}" width="8" height="8" rx="2" '
                 f'fill="{ACCENT if on else _t["fg"]}"{op}/>')
    return css, body


def ragflow(_t):
    css, body = "", monitor("")
    ys = [24, 50, 76]
    for i, y in enumerate(ys):
        cid = f"rg{i}"
        css += appear(cid, 0.05 + i * 0.15, 0.92, 8)
        body += (f'<rect class="ln" x="12" y="{y}" width="52" height="18" rx="4"/>'
                 f'<rect class="{cid}" x="12" y="{y}" width="52" height="18" rx="4" '
                 f'fill="none" stroke="{ACCENT}" stroke-width="1.5" opacity="0"/>'
                 f'<line class="hair" x1="64" y1="{y + 9}" x2="100" y2="52"/>')
    body += (f'<rect class="ln" x="100" y="18" width="86" height="68" rx="6"/>'
             f'<circle cx="112" cy="30" r="3" fill="{ACCENT}"/>')
    for j in range(3):
        cid = f"ra{j}"
        css += appear(cid, 0.35 + j * 0.12, 0.92, 8)
        body += (f'<rect class="{cid}" x="122" y="{26 + j * 13}" width="{52 - j * 8}" height="5" rx="2.5" '
                 f'fill="{_t["fg"]}" fill-opacity=".45" opacity="0"/>')
    body += (f'<path d="M112,72 l4,4 l8,-9" fill="none" stroke="{ACCENT}" '
             f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>')
    return css, body


def pipeline(_t):
    css, body = "", monitor("")
    for i in range(3):
        cid = f"pp{i}"
        css += appear(cid, 0.05 + i * 0.2, 0.92, 8)
        x = 26 + i * 58
        body += (f'<rect class="ln" x="{x}" y="38" width="46" height="24" rx="12"/>'
                 f'<rect class="{cid}" x="{x}" y="38" width="46" height="24" rx="12" '
                 f'fill="none" stroke="{ACCENT}" stroke-width="1.5" opacity="0"/>')
        if i < 2:
            lid = f"pl{i}"
            css += appear(lid, 0.18 + i * 0.2, 0.92, 8)
            body += (f'<line class="{lid}" x1="{x + 48}" y1="50" x2="{x + 56}" y2="50" '
                     f'stroke="{ACCENT}" stroke-width="1.5" opacity="0"/>')
    css += appear("prs", 0.6, 0.92, 8)
    body += (f'<circle class="prs" cx="100" cy="84" r="4.5" fill="{ACCENT}" opacity="0"/>')
    return css, body


def hub(_t):
    css, body = "", monitor("")
    cx, cy = 100, 48
    body += f'<circle cx="{cx}" cy="{cy}" r="10" fill="{ACCENT}" fill-opacity=".8"/>'
    for i, (x, y) in enumerate([(46, 28), (154, 28), (100, 84)]):
        lid, nid = f"hl{i}", f"hn{i}"
        css += appear(lid, 0.1 + i * 0.15, 0.92, 8) + appear(nid, 0.15 + i * 0.15, 0.92, 8)
        body += (f'<line class="{lid}" x1="{cx}" y1="{cy}" x2="{x}" y2="{y}" '
                 f'stroke="{ACCENT}" stroke-width="1.2" opacity="0"/>'
                 f'<circle class="{nid}" cx="{x}" cy="{y}" r="7" fill="none" '
                 f'stroke="{_t["fg"]}" stroke-opacity=".6" opacity="0"/>')
    return css, body


def blocks(_t):
    css, body = "", monitor("")
    for i, y in enumerate([16, 42, 68]):
        cid = f"bk{i}"
        css += appear(cid, 0.05 + i * 0.22, 0.5 + i * 0.22, 7)
        body += (f'<rect class="ln" x="60" y="{y}" width="80" height="18" rx="4"/>'
                 f'<rect class="{cid}" x="60" y="{y}" width="80" height="18" rx="4" '
                 f'fill="{ACCENT}" fill-opacity=".3" opacity="0"/>')
        if i < 2:
            body += f'<line class="hair" x1="100" y1="{y + 18}" x2="100" y2="{y + 24}"/>'
    return css, body


def detect(_t):
    def corners(cid, x, y, w, h):
        L = 9
        d = (f"M{x},{y + h}V{y + L}Q{x},{y} {x + L},{y} "
             f"M{x + w - L},{y}H{x + w}V{y + L} "
             f"M{x + w},{y + h - L}V{y + h}H{x + w - L} "
             f"M{x + L},{y + h}H{x}V{y + h - L}")
        return (f'<path class="{cid}" d="{d}" fill="none" stroke="{ACCENT}" '
                f'stroke-width="2" stroke-linecap="round" opacity="0"/>')

    css = "".join(appear(f"dt{i}", 0.15 + i * 0.25, 0.92, 8) for i in range(2))
    body = monitor(
        f'<rect x="52" y="20" width="96" height="64" rx="4" fill="{ACCENT}" fill-opacity=".18"/>'
        f'<circle cx="84" cy="48" r="10" fill="{ACCENT}" fill-opacity=".5"/>'
        f'<rect x="108" y="40" width="24" height="30" rx="3" fill="{_t["fg"]}" fill-opacity=".25"/>'
        f'{corners("dt0", 70, 34, 28, 28)}{corners("dt1", 104, 36, 32, 38)}')
    return css, body


def seal(_t):
    css = appear("sl", 0.3, 0.9, 8)
    body = monitor(
        f'<rect x="62" y="18" width="76" height="68" rx="4" class="ln"/>'
        f'<rect class="fill" x="72" y="30" width="56" height="4" fill-opacity=".3"/>'
        f'<rect class="fill" x="72" y="40" width="40" height="4" fill-opacity=".2"/>'
        f'<rect class="fill" x="72" y="50" width="48" height="4" fill-opacity=".2"/>'
        f'<circle class="sl" cx="128" cy="70" r="12" fill="none" stroke="{ACCENT}" '
        f'stroke-width="2" opacity="0"/>'
        f'<path class="sl" d="M122,70 l4.5,4.5 l9,-10" fill="none" stroke="{ACCENT}" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" opacity="0"/>')
    return css, body


def typing(_t):
    css = ("@keyframes tp{0%,100%{transform:translateY(0);opacity:.4}50%{transform:translateY(-3px);opacity:1}}"
           ".tp{animation:tp 1.2s ease-in-out infinite}"
           + appear("tr", 0.45, 0.9, 8))
    dots = "".join(
        f'<circle class="tp" cx="{40 + i * 12}" cy="52" r="3.5" fill="{ACCENT}" '
        f'style="animation-delay:-{i * 0.2:.1f}s"/>' for i in range(3))
    body = monitor(
        f'<rect class="ln" x="56" y="34" width="88" height="30" rx="15"/>{dots}'
        f'<rect class="tr" x="56" y="72" width="88" height="9" rx="4.5" fill="{ACCENT}" '
        f'fill-opacity=".5" opacity="0"/>')
    return css, body


def notch(_t):
    eq = "".join(
        f'<rect class="eq eq{i}" x="{86 + i * 12}" y="52" width="7" height="18" rx="3.5" fill="{ACCENT}"/>'
        for i in range(3))
    css = ("@keyframes eq{0%,100%{transform:scaleY(.25)}50%{transform:scaleY(1)}}"
           ".eq{transform-box:fill-box;transform-origin:50% 100%;animation:eq 1.2s ease-in-out infinite}"
           ".eq1{animation-delay:-.4s}.eq2{animation-delay:-.8s}"
           "@keyframes pr{from{transform:scaleX(.05)}to{transform:scaleX(1)}}"
           ".pr{transform-box:fill-box;transform-origin:0 50%;animation:pr 4s linear infinite}\n")
    body = monitor(
        f'<rect x="45" y="8" width="110" height="24" rx="12" fill="none" stroke="{_t["fg"]}" stroke-opacity=".55"/>'
        f'<circle cx="57" cy="20" r="3" fill="{ACCENT}"/>{eq}'
        f'<rect x="45" y="82" width="110" height="4" rx="2" fill="{_t["fg"]}" fill-opacity=".18"/>'
        f'<rect class="pr" x="45" y="82" width="110" height="4" rx="2" fill="{ACCENT}"/>')
    return css, body




def strip(_t):
    wins = "".join(
        f'<rect class="ln" x="{6 + i * 66}" y="30" width="58" height="66" rx="3"/>'
        + "".join(f'<rect class="fill" x="{15 + i * 66}" y="{40 + j * 9}" width="{34 - j * 7}" height="3" fill-opacity=".3"/>'
                   for j in range(3))
        for i in range(4))
    css = ("@keyframes st{0%,16%{transform:none}30%,46%{transform:translate(-66px)}"
           "60%,76%{transform:translate(-132px)}90%,100%{transform:none}}"
           ".st{animation:st 9s cubic-bezier(.6,0,.2,1) infinite}\n")
    body = (f'<rect class="ln" x=".5" y=".5" width="199" height="103" rx="6"/>'
            f'<clipPath id="stc"><rect x="4" y="8" width="192" height="88"/></clipPath>'
            f'<g clip-path="url(#stc)"><g class="st">{wins}</g></g>'
            f'<rect x="70.5" y="29.5" width="59" height="67" rx="3" fill="none" stroke="{ACCENT}" stroke-width="1.5"/>')
    return css, body




def shrink(_t):
    css = ("@keyframes sh{0%,14%{transform:scale(1) translate(0,0);opacity:1}"
           "45%,70%{transform:scale(.18) translate(150px,52px);opacity:1}"
           "84%,100%{transform:scale(1) translate(0,0);opacity:1}}"
           ".sh{transform-box:fill-box;transform-origin:0 0;animation:sh 7s cubic-bezier(.5,0,.3,1) infinite}"
           + BLINK)
    body = monitor(
        f'<g class="sh"><rect class="ln" x="52" y="24" width="96" height="56" rx="4"/>'
        f'<rect class="fill" x="60" y="34" width="50" height="4" fill-opacity=".4"/>'
        f'<rect class="fill" x="60" y="43" width="66" height="4" fill-opacity=".25"/></g>'
        f'<rect x="150" y="86" width="34" height="10" rx="5" fill="{ACCENT}"/>'
        f'<circle class="bl" cx="192" cy="91" r="2.5" fill="{ACCENT}"/>')
    return css, body




def needle(_t):
    import math
    css = ("@keyframes nd{0%,100%{transform:rotate(-38deg)}50%{transform:rotate(38deg)}}"
           ".nd{transform-box:fill-box;transform-origin:50% 100%;animation:nd 3.2s ease-in-out infinite}\n")
    ticks = "".join(
        f'<line class="ln" x1="100" y1="78" x2="{100 + 52 * math.cos(a):.0f}" '
        f'y2="{78 + 52 * math.sin(a):.0f}"/>'
        for a in [3.66, 3.93, 4.19, 4.45, 4.71, 4.97, 5.24, 5.5, 5.76])
    body = monitor(
        f'{ticks}<circle cx="100" cy="78" r="4" fill="{ACCENT}"/>'
        f'<g class="nd"><line x1="100" y1="78" x2="100" y2="34" stroke="{ACCENT}" '
        f'stroke-width="2.5" stroke-linecap="round"/></g>')
    return css, body




def book(_t):
    css = "".join(appear(f"pg{i}", 0.08 + i * 0.16, 0.92, 8) for i in range(4))
    lines = "".join(
        f'<rect class="fill pg{i}" x="60" y="{34 + i * 11}" width="{80 - i * 9}" height="3.5" fill-opacity=".4" opacity="0"/>'
        for i in range(4))
    body = monitor(
        f'<path class="ln" d="M100,22 C86,16 70,16 58,20 V84 C70,80 86,80 100,86 '
        f'C114,80 130,80 142,84 V20 C130,16 114,16 100,22 Z"/>'
        f'<line class="ln" x1="100" y1="22" x2="100" y2="86"/>{lines}'
        f'<rect x="136" y="14" width="10" height="22" rx="2" fill="{ACCENT}"/>')
    return css, body








def ring(_t):
    css = ("@keyframes rg{from{stroke-dashoffset:0}to{stroke-dashoffset:1}}"
           ".rg{animation:rg 6s linear infinite}\n")
    body = monitor(
        f'<circle cx="100" cy="52" r="30" fill="none" stroke="{_t["fg"]}" stroke-opacity=".2" stroke-width="5"/>'
        f'<circle class="rg" cx="100" cy="52" r="30" fill="none" stroke="{ACCENT}" stroke-width="5" '
        f'stroke-linecap="round" pathLength="1" stroke-dasharray="1" transform="rotate(-90 100 52)"/>'
        f'<circle cx="100" cy="52" r="4" fill="{ACCENT}"/>')
    return css, body




def meter(_t):
    css = ("@keyframes mt{0%,8%{transform:scaleX(.04)}70%,88%{transform:scaleX(1)}96%,100%{transform:scaleX(.04)}}"
           ".mt{transform-box:fill-box;transform-origin:0 50%;animation:mt 7s ease-in-out infinite}\n")
    ticks = "".join(f'<line class="ln" x1="{30 + i * 35}" y1="30" x2="{30 + i * 35}" y2="38"/>' for i in range(5))
    body = monitor(
        f'{ticks}<rect x="24" y="46" width="152" height="16" rx="8" fill="none" '
        f'stroke="{_t["fg"]}" stroke-opacity=".4"/>'
        f'<rect class="mt" x="24" y="46" width="152" height="16" rx="8" fill="{ACCENT}" fill-opacity=".85"/>')
    return css, body




def tiles(_t):
    css, body = "", monitor("")
    for i, (x, y, w, h) in enumerate([(14, 14, 110, 76), (130, 14, 56, 36), (130, 56, 56, 34)]):
        on = (i * 0.3) % 0.9
        css += appear(f"tl{i}", on, on + 0.28, 9)
        body += (f'<rect class="ln" x="{x}" y="{y}" width="{w}" height="{h}" rx="3"/>'
                 f'<rect class="tl{i}" x="{x}" y="{y}" width="{w}" height="{h}" rx="3" '
                 f'fill="none" stroke="{ACCENT}" stroke-width="1.6" opacity="0"/>')
    return css, body




def filmstrip(_t):
    arts = [
        f'<circle cx="28" cy="52" r="10" fill="{ACCENT}" fill-opacity=".5"/>',
        f'<polygon points="28,42 38,60 18,60" fill="{_t["fg"]}" fill-opacity=".35"/>',
        f'<rect x="20" y="44" width="16" height="16" rx="2" fill="{_t["fg"]}" fill-opacity=".35"/>',
        f'<rect x="18" y="48" width="20" height="4" fill="{ACCENT}" fill-opacity=".6"/>'
        f'<rect x="18" y="55" width="13" height="4" fill="{_t["fg"]}" fill-opacity=".3"/>',
    ]
    frames = ""
    for k in range(5):
        x = -64 + k * 64
        frames += (f'<rect x="{x + 4}" y="30" width="56" height="44" rx="3" fill="none" '
                   f'stroke="{_t["fg"]}" stroke-opacity=".4"/>'
                   f'<g transform="translate({x + 4},0)">{arts[k % 4]}</g>')
        for hx in (x + 10, x + 26, x + 42):
            frames += (f'<rect x="{hx}" y="20" width="6" height="5" rx="1.5" '
                       f'fill="{_t["fg"]}" fill-opacity=".25"/>'
                       f'<rect x="{hx}" y="79" width="6" height="5" rx="1.5" '
                       f'fill="{_t["fg"]}" fill-opacity=".25"/>')
    css = ("@keyframes fl{0%{transform:translate(0)}85%,100%{transform:translate(-256px)}}"
           ".fl{animation:fl 7s cubic-bezier(.6,0,.2,1) infinite}\n")
    body = monitor(
        f'<clipPath id="flm"><rect x="4" y="14" width="192" height="76"/></clipPath>'
        f'<g clip-path="url(#flm)"><g class="fl">{frames}</g></g>'
        f'<rect x="68" y="28" width="64" height="48" rx="4" fill="none" stroke="{ACCENT}" stroke-width="1.6"/>')
    return css, body


def neural(_t):
    cols = [[112, [34, 52, 70]], [142, [28, 43, 58, 73]], [172, [40, 64]]]
    edges = "".join(
        f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y1}" stroke="{_t["fg"]}" stroke-opacity=".22"/>'
        for (x0, ys0), (x1, ys1) in zip(cols, cols[1:])
        for y0 in ys0 for y1 in ys1)
    nodes, css = "", ""
    for ci, (x, ys) in enumerate(cols):
        cid = f"nn{ci}"
        css += appear(cid, 0.05 + ci * 0.25, 0.92, 7)
        for y in ys:
            nodes += (f'<circle class="{cid}" cx="{x}" cy="{y}" r="4" fill="{ACCENT}" '
                      f'fill-opacity=".75" opacity="0"/>'
                      f'<circle cx="{x}" cy="{y}" r="4" fill="none" stroke="{_t["fg"]}" stroke-opacity=".4"/>')
    css += ("@keyframes np{0%{transform:translate(0);opacity:0}12%{opacity:1}70%{opacity:1}"
            "88%,100%{transform:translate(60px);opacity:0}}.np{animation:np 7s linear infinite}\n")
    paw = (f'<ellipse cx="48" cy="60" rx="10" ry="8" fill="{ACCENT}" fill-opacity=".4"/>'
           + "".join(f'<circle cx="{x}" cy="{y}" r="3.6" fill="{_t["fg"]}" fill-opacity=".45"/>'
                     for x, y in [(33, 46), (42, 40), (54, 40), (63, 46)]))
    body = monitor(
        f"{paw}{edges}{nodes}"
        f'<circle class="np" cx="112" cy="52" r="3" fill="{ACCENT}" opacity="0"/>')
    return css, body


SCENES = {"bars": bars, "branch": branch, "wave": wave,
          "gauge": gauge, "chart": chart, "scan": scan, "grid": grid,
          "neural": neural, "ragflow": ragflow, "pipeline": pipeline,
          "hub": hub, "blocks": blocks, "detect": detect,
          "notch": notch, "strip": strip, "shrink": shrink,
          "needle": needle, "book": book,
          "seal": seal, "typing": typing, "filmstrip": filmstrip,
          "ring": ring, "meter": meter, "tiles": tiles}


# ------------------------------------------------------------------ rows -

ROW_H = 134
NAME_SIZE = 28


def section_pill(theme, i, title, count):
    key = f"sec{i}"
    body = (
        f'<line class="hair" x1="{PAD}" x2="{W - PAD}" y1=".5" y2=".5"/>'
        f'<text class="d acc" x="{PAD - 2}" y="62" font-size="34">{T(key, title.upper(), "disp")}</text>'
    )
    return svg(key, theme, 76, "", body, f"{title}, {count} projects")




def row(theme, card, idx):
    global _CUR
    t = THEMES[theme]
    key = f"row-{card['name']}"
    _CUR = key
    name = trunc(card["disp"], "disp", NAME_SIZE, 560)
    name_w = text_w(name, "disp", NAME_SIZE)
    lines = wrap(card["desc"], "mono", 11, 600)
    if len(lines) > 2:
        lines = lines[:2]
        lines[1] = trunc(lines[1], "mono", 11, 600)
    stack_y = 88 + 16 * (len(lines) - 1) + 18
    H = max(134, stack_y + 20)
    sy = (H - 104) / 2
    y = 32
    edge = W - PAD - 200 - 12  # marker zone ends left of the scene
    marker = ""
    if card.get("live"):
        ltw = text_w("live", "mono", 10)
        cX = edge - (14 + 7 + 8 + ltw + 8 + 7 + 14)
        marker = (f'<rect x="{cX:.0f}" y="18" width="{(28 + ltw + 23):.0f}" height="26" rx="6" '
                  f'fill="none" stroke="{t["hair"]}" stroke-width="1"/>'
                  f'<circle class="bl" cx="{cX + 14 + 3.5:.0f}" cy="31" r="3.5" fill="{ACCENT}"/>'
                  f'<text class="m" x="{cX + 14 + 7 + 8:.0f}" y="35" font-size="10">{T(key, "live")}</text>'
                  f'<g transform="translate({cX + 14 + 7 + 8 + ltw + 8:.0f},24)">{arrow(0, 0, 7)}</g>')
    sc = card["scene"]
    if sc == "bars":
        scss, sbody = SCENES[sc](t, *card.get("args", ()))
    else:
        scss, sbody = SCENES[sc](t)
    _CUR = None
    body = (
        f'<line class="hair" x1="{PAD}" x2="{W - PAD}" y1=".5" y2=".5"/>'
        f'<text class="m acc" x="30" y="{y}">{idx:02d}</text>'
        f'<text class="d" x="28" y="64" font-size="{NAME_SIZE}">{T(key, name, "disp")}</text>'
        f'<g transform="translate({28 + name_w + 14:.0f},42)">{arrow(0, 0, 12)}</g>'
        + "".join(
            f'<text class="m dim" x="30" y="{88 + i * 16}">{T(key, ln)}</text>'
            for i, ln in enumerate(lines))
        + f'<text class="m acc" x="30" y="{stack_y}" font-size="10.5">{T(key, card["stack"])}</text>'
        + f"{marker}"
        + f'<g transform="translate({W - PAD - 200},{sy:.0f})">{sbody}</g>'
    )
    css = BLINK + scss
    label = f"{card['disp']}: {card['desc']} {card['stack']}" + (" (live)" if card.get("live") else "")
    return svg(key, theme, H, css, body, label)


SECTIONS = [
    ("personal site / wiki", [
        {"name": "wiki", "disp": "PERSONAL WIKI", "scene": "ragflow", "live": True,
         "desc": "private knowledge assistant using rag for personal information and resumes.",
         "stack": "jekyll · rag",
         "url": f"https://{USER}.github.io"},
        {"name": "365DaysOfData", "disp": "365DAYSOFDATA", "scene": "grid",
         "desc": "year-long AI log",
         "stack": "python · rag · agents",
         "stars": data["flag_stars"]},
    ]),
    ("fullstack ai", [
        {"name": "nyayak", "disp": "NYAYAK", "scene": "seal", "live": True,
         "desc": "legal ai platform combining rag, lawyer discovery, court navigation, and forums.",
         "stack": "typescript · python"},
        {"name": "meantrainer", "disp": "MEANTRAINER", "scene": "wave", "live": True,
         "desc": "ai fitness coach generating personalized workouts and diets through voice.",
         "stack": "next.js · typescript"},
    ]),
    ("machine learning", [
        {"name": "ML-Based-Football-Players-Market-Value-Prediction", "disp": "FOOTBALL MARKET VALUE",
         "scene": "chart",
         "desc": "predicts footballer market values using 18k+ records and machine learning.",
         "stack": "python · scikit-learn"},
        {"name": "cineRank", "disp": "CINERANK", "scene": "gauge",
         "desc": "movie platform combining bert sentiment analysis with personalized recommendations.",
         "stack": "python · transformers",
         "url": "https://cine-rank.vercel.app"},
        {"name": "Movie-Recommender-System", "disp": "MOVIE-RECOMMENDER", "scene": "filmstrip",
         "desc": "TF-IDF, 5k movies",
         "stack": "tf-idf · streamlit"},
    ]),
    ("deep learning", [
        {"name": "cat-vs-dog-classifier", "disp": "CAT VS DOG CLASSIFIER", "scene": "neural",
         "desc": "computer vision classifier identifying cats and dogs using vgg16 transfer-learning.",
         "stack": "pytorch · streamlit"},
        {"name": "guess-footballer-with-eyes", "disp": "GUESS THE FOOTBALLER", "scene": "scan",
         "desc": "computer vision project recognizing footballers from eye images using resnet18.",
         "stack": "pytorch · opencv"},
        {"name": "Image-Captioning-Transformer", "disp": "IMAGE CAPTIONING", "scene": "detect",
         "desc": "generates natural-language image descriptions using resnet18 and transformer architectures.",
         "stack": "pytorch · transformers"},
        {"name": "seq2seq-chatbot", "disp": "SEQ2SEQ CHATBOT", "scene": "typing",
         "desc": "conversational chatbot built with bidirectional gru and luong attention.",
         "stack": "pytorch · gru"},
        {"name": "GPT-From-Scratch", "disp": "GPT FROM SCRATCH", "scene": "blocks",
         "desc": "from-scratch transformer language model implementing attention, residuals, and normalization.",
         "stack": "pytorch · transformers"},
        {"name": "Choose-Your-Own-Adventure", "disp": "CHOOSE YOUR ADVENTURE", "scene": "branch",
         "desc": "interactive ai storytelling platform featuring branching narratives and dynamic exploration.",
         "stack": "ollama · llama 3.2"},
    ]),
    ("linux and shell", [
        {"name": "notch-island", "disp": "NOTCH-ISLAND", "scene": "notch", "live": True,
         "desc": "Edge-anchored notch / pill for Omarchy: dock, clock, media island, and quick set",
         "stack": "qml · quickshell"},
        {"name": "bhagwat-geeta", "disp": "BHAGWAT-GEETA", "scene": "book",
         "desc": "pocket geeta for quickshell",
         "stack": "qml · quickshell"},
        {"name": "switcher", "disp": "SWITCHER", "scene": "strip",
         "desc": "niri alt-tab for Omarchy",
         "stack": "omarchy · wayland"},
        {"name": "opencode-usage", "disp": "OPENCODE-USAGE", "scene": "bars",
         "desc": "model usage tracker",
         "stack": "tracker · api"},
        {"name": "guitar", "disp": "GUITAR", "scene": "needle",
         "desc": "practice plugin + metronome + tuner",
         "stack": "practice · audio"},
        {"name": "agebar", "disp": "AGEBAR", "scene": "meter",
         "desc": "aging widget",
         "stack": "quickshell · time"},
        {"name": "minimize-pill", "disp": "MINIMIZE-PILL", "scene": "shrink",
         "desc": "Hyprland minimizer",
         "stack": "hyprland · quickshell"},
        {"name": "dotfiles", "disp": "DOTFILES", "scene": "tiles",
         "desc": "Niri + Quickshell config",
         "stack": "niri · dotfiles"},
        {"name": "countdown-gnome-extension", "disp": "COUNTDOWN", "scene": "ring",
         "desc": "GNOME top-bar countdown",
         "stack": "gnome · js"},
    ]),
    ("collections", [
        {"name": "agents", "disp": "AGENTIC AI PROJECTS", "scene": "hub",
         "desc": "autonomous ai agents exploring memory, tools, mcp, and multi-agent debate.",
         "stack": "langgraph · mcp",
         "url": f"https://github.com/{USER}/365DaysOfData/tree/main/16-Project-Based-AgenticAI"},
        {"name": "genai", "disp": "GENAI MINI PROJECTS", "scene": "pipeline",
         "desc": "experiments spanning rag, qlora fine-tuning, evaluation, and multimodal generation.",
         "stack": "qlora · deepeval",
         "url": f"https://github.com/{USER}/365DaysOfData/tree/main/15-Projects-Based-GenAI"},
        {"name": "EDA-Projects", "disp": "EDA PROJECTS", "scene": "bars",
         "desc": "data exploration projects uncovering patterns through statistics and visualizations.",
         "stack": "pandas · matplotlib"},
    ]),
]

CARDS = os.path.join(HERE, "cards")
os.makedirs(CARDS, exist_ok=True)
REPO = f"https://github.com/{USER}"

jobs = [("header", f"https://{USER}.github.io", header)]
for si, (title, cards) in enumerate(SECTIONS, 1):
    jobs.append((f"sec{si}", None,
                 lambda th, si=si, title=title, cards=cards:
                 section_pill(th, si, title, len(cards))))
    for ci, card in enumerate(cards, 1):
        url = card.get("url", f"{REPO}/{card['name']}")
        jobs.append((f"row-{card['name']}", url,
                     lambda th, card=card, ci=ci: row(th, card, ci)))

RAW = f"https://raw.githubusercontent.com/{USER}/{USER}/main/profile/cards/"
alts = {}
import xml.dom.minidom as _minidom
for name, _url, make in jobs:
    for theme in THEMES:
        out = make(theme)
        _minidom.parseString(out)  # fail loudly on malformed SVG
        alts[name] = re.search(r'aria-label="([^"]*)"', out).group(1)
        with open(os.path.join(CARDS, f"{name}-{theme}.svg"), "w") as f:
            f.write(out)
        kb = len(out.encode()) / 1024
        if kb > 60:
            print(f"warn: {name}-{theme}.svg is {kb:.0f} KB", file=sys.stderr)

WORKFLOW = os.path.join(ROOT, ".github", "workflows", "profile.yml")
os.makedirs(os.path.dirname(WORKFLOW), exist_ok=True)
with open(WORKFLOW, "w") as f:
    f.write("""name: profile
on:
  schedule: [{cron: "0 0 * * *"}]
  workflow_dispatch:
permissions:
  contents: write
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.12"}
      - run: pip install fonttools
      - run: python3 profile/build.py
        env: {GITHUB_TOKEN: "${{ secrets.GITHUB_TOKEN }}"}
      - run: |
          git config user.name github-actions
          git config user.email github-actions@github.com
          git add profile README.md
          git diff --cached --quiet || git commit -m "profile: rebuild rows"
          git push
""")


def pic(name, url):
    alt = hesc(alts[name])
    head = (f'<a href="{url}">' if url else "")
    tail = "</a>" if url else ""
    return (f'{head}<picture><source media="(prefers-color-scheme: dark)" '
            f'srcset="{RAW}{name}-dark.svg">'
            f'<img src="{RAW}{name}-light.svg" width="100%" alt="{alt}"></picture>{tail}')


with open(os.path.join(ROOT, "README.md"), "w") as f:
    f.write("<!-- Generated by profile/build.py: edit that and rebuild, not this file. -->\n\n")
    f.write("\n".join(pic(n, u) for n, u, _m in jobs))
    f.write("\n")

print(f"{len(jobs) * 2} SVGs, workflow and README.md written")
