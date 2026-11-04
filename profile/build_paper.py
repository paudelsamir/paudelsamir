#!/usr/bin/env python3
"""Research-paper layout for the profile README (local preview only).

Typeset with Computer Modern (the LaTeX face): centred title block,
abstract, keywords, numbered sections, a booktabs-style table and a page
number. Light and dark variants are picked by <picture>; the markdown
reference index underneath carries the working links.

  python3 profile/build_paper.py

Writes profile/cards-paper/paper-{light,dark}.svg, README.paper.md and
preview-paper-{light,dark}.html. Nothing is pushed.
"""

import base64
import io
import os
import re
import sys
from html import escape as hesc

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
USER = "paudelsamir"
W = 880
M = 72
X0, X1 = M, W - M

THEMES = {
    "light": {"bg": "#ffffff", "ink": "#000000", "mut": "#000000",
              "rule": "#808080", "faint": "#cccccc", "acc": "#125a54"},
    "dark": {"bg": "#15130f", "ink": "#eae4d6", "mut": "#a49a87",
             "rule": "#5a5344", "faint": "#2f2a21", "acc": "#5cc6b9"},
}

_local_fonts = os.path.join(HERE, "fonts")
FD = (os.environ.get("PAPER_FONT_DIR")
      or (_local_fonts if os.path.exists(os.path.join(_local_fonts, "cmunrm.otf"))
          else "/tmp/opencode/fonts/cmu"))
FONT_FILES = {
    "R": os.path.join(FD, "cmunrm.otf"),   # roman
    "B": os.path.join(FD, "cmunbx.otf"),   # bold
    "I": os.path.join(FD, "cmunti.otf"),   # italic
    "T": os.path.join(FD, "cmuntt.otf"),   # typewriter
}

# ------------------------------------------------------------------ data --
# PORTFOLIO is loaded further below from profile/portfolio.py

GROUP_LABEL = {
    "personal site / wiki": "Retrieval and interfaces",
    "fullstack ai": "Full-stack systems",
    "machine learning": "Machine learning",
    "deep learning": "Deep learning",
    "linux and shell": "Linux and shell",
    "collections": "Collections",
}

SYSTEM_NAME = {
    "wiki": "Personal Wiki", "365DaysOfData": "365 Days of Data",
    "nyayak": "Nyayak", "meantrainer": "Meantrainer",
    "ML-Based-Football-Players-Market-Value-Prediction": "Football Market Value",
    "cineRank": "CineRank", "Movie-Recommender-System": "Movie Recommender",
    "cat-vs-dog-classifier": "Cat vs. Dog", "guess-footballer-with-eyes": "Guess the Footballer",
    "Image-Captioning-Transformer": "Image Captioning", "seq2seq-chatbot": "Seq2SEQ Chatbot",
    "GPT-From-Scratch": "GPT from Scratch", "Choose-Your-Own-Adventure": "Choose Your Own Adventure",
    "notch-island": "Notch Island", "bhagwat-geeta": "Bhagwat Geeta",
    "switcher": "Switcher", "opencode-usage": "OpenCode Usage",
    "guitar": "Guitar", "agebar": "Agebar", "minimize-pill": "Minimize Pill",
    "dotfiles": "Dotfiles", "countdown-gnome-extension": "Countdown",
    "agents": "Agentic AI Projects", "genai": "GenAI Mini Projects",
    "EDA-Projects": "EDA Projects",
}

CONTRIBUTION = {
    "wiki": "Private RAG over notes and resumes",
    "365DaysOfData": "A year-long log of AI experiments",
    "nyayak": "Legal RAG, lawyer discovery, court navigation",
    "meantrainer": "Voice-driven workout and diet coach",
    "ML-Based-Football-Players-Market-Value-Prediction": "Market value from 18k player records",
    "cineRank": "BERT sentiment meets movie rankings",
    "Movie-Recommender-System": "TF-IDF recommendations over 5k films",
    "cat-vs-dog-classifier": "VGG16 transfer-learning classifier",
    "guess-footballer-with-eyes": "Player identification from eye crops",
    "Image-Captioning-Transformer": "ResNet encoder, transformer decoder",
    "seq2seq-chatbot": "GRU encoder with Luong attention",
    "GPT-From-Scratch": "Transformer language model from scratch",
    "Choose-Your-Own-Adventure": "Branching narratives via a local LLM",
    "notch-island": "Dock, clock, media and quick settings",
    "bhagwat-geeta": "Pocket Gita reader for the shell",
    "switcher": "Niri-style alt-tab for Omarchy",
    "opencode-usage": "Per-model usage and quota tracker",
    "guitar": "Metronome, tuner, and practice log",
    "agebar": "A quiet reminder that time passes",
    "minimize-pill": "Minimal Hyprland window minimizer",
    "dotfiles": "Niri and Quickshell desktop config",
    "countdown-gnome-extension": "GNOME top-bar countdown",
    "agents": "Memory, tools, MCP, multi-agent debate",
    "genai": "RAG, QLoRA, evaluation, multimodal",
    "EDA-Projects": "Statistical exploration notebooks",
}

# ---------------------------------------------- portfolio projects (48) --

_pf = os.path.join(HERE, "portfolio.py")
if os.path.exists(_pf):
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location("portfolio_data", _pf)
    _mod = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    PORTFOLIO = _mod.PORTFOLIO
else:  # fallback to the old build.py sections
    PORTFOLIO = [(GROUP_LABEL.get(t, t), [
        {"title": SYSTEM_NAME.get(c["name"], c["disp"].title()),
         "desc": CONTRIBUTION.get(c["name"], c["desc"]),
         "stack": c["stack"],
         "url": c.get("url", f"https://github.com/{USER}/{c['name']}"),
         "live": bool(c.get("live"))}
        for c in cards]) for t, cards in SECTIONS]


# ----------------------------------------------------------------- fonts --

FONTS = {}


def load_font(path):
    from fontTools.ttLib import TTFont
    font = TTFont(path)
    return font, font["head"].unitsPerEm, font["hmtx"], font.getBestCmap()


for _k, _p in FONT_FILES.items():
    if os.path.exists(_p):
        FONTS[_k] = load_font(_p)
    else:
        print(f"missing font {_p}", file=sys.stderr)


def adv(ch, key, size):
    if key not in FONTS:
        return size * 0.5
    _f, upm, hmtx, cmap = FONTS[key]
    glyph = cmap.get(ord(ch), cmap.get(ord(" "), ".notdef"))
    try:
        w = hmtx[glyph][0]
    except KeyError:
        w = hmtx[cmap.get(ord(" "))][0]
    return w / upm * size


def tw(s, key, size):
    return sum(adv(c, key, size) for c in s)


def trunc(s, key, size, width):
    if tw(s, key, size) <= width:
        return s
    while s and tw(s + "…", key, size) > width:
        s = s[:-1]
    return s + "…"


def flow(text, key, size, width):
    words, lines, cur = text.split(), [], []
    for wd in words:
        trial = " ".join(cur + [wd])
        if tw(trial, key, size) <= width or not cur:
            cur.append(wd)
        else:
            lines.append(" ".join(cur))
            cur = [wd]
    if cur:
        lines.append(" ".join(cur))
    return lines


USED = {}


def T(font, s):
    USED.setdefault(font, set()).update(s)
    return hesc(s)


def subset_b64(path, chars):
    from fontTools import subset
    from fontTools.ttLib import TTFont
    opts = subset.Options()
    opts.flavor = "woff"
    opts.drop_tables += ["PfEd", "LTSH", "VDMX", "hdmx", "gasp", "kern"]
    font = TTFont(path)
    ss = subset.Subsetter(opts)
    ss.populate(text="".join(sorted(chars)))
    ss.subset(font)
    buf = io.BytesIO()
    font.save(buf)
    return base64.b64encode(buf.getvalue()).decode()


def font_css():
    out = []
    for key, fam in (("R", "R"), ("B", "B"), ("I", "I"), ("T", "T")):
        chars = USED.get(key)
        path = FONT_FILES[key]
        if not chars or not os.path.exists(path):
            continue
        out.append(
            f"@font-face{{font-family:{fam};src:url(data:font/woff;base64,"
            f"{subset_b64(path, chars)}) format('woff')}}"
        )
    return "".join(out)


# --------------------------------------------------------------- drawing --

class Page:
    def __init__(self, theme):
        self.t = THEMES[theme]
        self.parts = []

    # -- primitives ----------------------------------------------------
    def hline(self, x0, x1, y, color, h=0.8):
        self.parts.append(f'<rect x="{x0}" y="{y:.1f}" width="{x1 - x0:.1f}" '
                          f'height="{h}" fill="{color}"/>')

    def text(self, x, y, s, key="R", size=10.5, cls="ink", anchor="start",
             tracking=None, word_space=None, fill=None):
        if fill is None:
            fill = self.t.get(cls, self.t["ink"])
        attrs = [f'x="{x:.1f}"', f'y="{y:.1f}"', f'font-size="{size}"',
                 f'fill="{fill}"', f'class="{key} {cls}"']
        if anchor != "start":
            attrs.append(f'text-anchor="{anchor}"')
        if tracking:
            attrs.append(f'letter-spacing="{tracking * size:.2f}"')
        if word_space:
            attrs.append(f'word-spacing="{word_space:.2f}"')
        self.parts.append(f'<text {" ".join(attrs)}>{T(key, s)}</text>')
        n = len(s)
        return tw(s, key, size) + (tracking * size * (n - 1) if tracking and n else 0)

    @staticmethod
    def sc_width(s, size=8.6, tracking=0.12):
        w = 0.0
        for ch in s:
            w += adv(ch.upper(), "R", size * (0.78 if ch.islower() else 1.0))
        return w + tracking * size * max(0, len(s) - 1)

    def smallcaps(self, x, y, s, size=8.6, cls="mut", anchor="start", tracking=0.12):
        """Uppercase with the original lowercase set smaller, like \\textsc."""
        width = self.sc_width(s, size, tracking)
        if anchor == "middle":
            x -= width / 2
        elif anchor == "end":
            x -= width
        tspans, cursor = [], x
        for i, ch in enumerate(s):
            fs = size * (0.78 if ch.islower() else 1.0)
            tspans.append(f'<tspan x="{cursor:.2f}" font-size="{fs:.2f}">'
                          f'{T("R", ch.upper())}</tspan>')
            cursor += adv(ch.upper(), "R", fs) + tracking * size
        _fill = self.t.get(cls, self.t["ink"])
        self.parts.append(f'<text y="{y:.1f}" fill="{_fill}" class="R {cls}">{"".join(tspans)}</text>')
        return width

    def para(self, x, y, width, text, size=10.4, lh=14.2, key="R", cls="ink",
             justify=True):
        lines = flow(text, key, size, width)
        for i, ln in enumerate(lines):
            last = i == len(lines) - 1
            ws = 0.0
            if justify and not last and " " in ln:
                ws = (width - tw(ln, key, size)) / ln.count(" ")
            self.text(x, y + i * lh, ln, key, size, cls, word_space=ws)
        return y + (len(lines) - 1) * lh

    def centered_para(self, y, width, text, size=10.4, lh=14.2, key="R",
                      cls="ink", justify=True):
        x = (W - width) / 2
        return self.para(x, y, width, text, size, lh, key, cls, justify)

    def finish(self, height, width=None, frame=True, label=None):
        t = self.t
        width = width or W
        css = (
            f".ink{{fill:{t['ink']}}}.mut{{fill:{t['mut']}}}.acc{{fill:{t['acc']}}}"
            f".R{{font-family:R,'Times New Roman',serif}}"
            f".B{{font-family:B,'Times New Roman',serif;font-weight:700}}"
            f".I{{font-family:I,'Times New Roman',serif;font-style:italic}}"
            f".T{{font-family:T,ui-monospace,monospace}}"
        )
        body = "".join(self.parts)
        if frame:
            body = (f'<rect x=".5" y=".5" width="{width - 1}" height="{height - 1}" '
                    f'fill="{t["bg"]}" stroke="{t["faint"]}" stroke-width="1"/>') + body
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            f'width="{width}" height="{height}" role="img" '
            f'aria-label="{hesc(label or "Samir Paudel: selected work.")}">'
            f"<style>{font_css()}{css}</style>{body}</svg>"
        )


# ---------------------------------------------------------------- layout --

TITLE = "Turning Data into Systems That Run"

ABSTRACT = ("This report documents twenty-five independent systems built between 2024 "
            "and 2026: retrieval-augmented interfaces, full-stack AI products, learning "
            "experiments, and Linux desktop tooling. Each entry states the problem, the "
            "method, and the stack on which it runs. The through-line is practical — "
            "models are treated as components of working software rather than as ends in "
            "themselves. All systems are open source, and live demonstrations are noted "
            "where they exist.")

KEYWORDS = ("retrieval-augmented generation · computer vision · language models · "
            "QML · reproducible software")

INTRO = ("Applied machine learning rarely fails at the model. It fails at the seams: a "
         "retrieval step that returns the right passage but the wrong version of it, an "
         "interface that cannot express uncertainty, a build that nobody else can "
         "reproduce. This report is organised around that observation. Section 2 "
         "catalogues twenty-five systems grouped by the problem they address rather than "
         "by the technique they use; Section 3 describes how the work is distributed and "
         "rebuilt. The selection is deliberately broad — from a small GNOME extension to "
         "a transformer language model written from scratch — because the same "
         "engineering discipline applies at every scale.")

SEC2 = ("Table 1 lists each system with its contribution and implementation stack; the "
        "index in Section 3 links to source and demonstrations. A filled circle marks a "
        "system with a public demo.")

SEC3 = ("Every system is public at github.com/paudelsamir. The index below links to the "
        "sources; live demos are hosted on Vercel, Streamlit, or GitHub Pages. This page "
        "is compiled daily from repository metadata by a small build script, so counts "
        "and status stay current without manual edits.")


def paper(theme):
    pg = Page(theme)
    t = pg.t

    # ---- masthead
    y = 40
    pg.text(X0, y, "PREPRINT · 2026.11", "T", 8.4, "mut", tracking=0.12)
    pg.text(X1, y, f"github.com/{USER}", "T", 8.4, "mut", anchor="end")
    pg.hline(X0, X1, y + 10, t["rule"], 1.2)

    # ---- title block
    y = 94
    pg.text(W / 2, y, TITLE, "B", 28, "ink", anchor="middle")
    y += 22
    pg.text(W / 2, y, "Samir Paudel", "R", 14.5, "ink", anchor="middle")
    y += 16
    pg.text(W / 2, y, "Independent researcher · Kathmandu, Nepal", "I", 10.2, "mut",
            anchor="middle")
    y += 14
    pg.text(W / 2, y, "paudelsamir.github.io · contact.samirpaudel@gmail.com", "T", 8.4,
            "mut", anchor="middle")
    y += 13
    pg.text(W / 2, y, "November 2026", "I", 9.4, "mut", anchor="middle")
    y += 14
    pg.hline(X0, X1, y, t["rule"], 0.7)

    # ---- abstract
    y += 22
    pg.smallcaps(W / 2, y, "Abstract", 9.0, "mut", anchor="middle", tracking=0.18)
    y += 16
    y = pg.centered_para(y, 650, ABSTRACT, 9.9, 13.6)

    y += 14
    kw_w = pg.sc_width("Keywords:", 8.4, 0.06)
    body_w = tw(KEYWORDS, "R", 9.2)
    start = (W - (kw_w + 6 + body_w)) / 2
    pg.smallcaps(start, y, "Keywords:", 8.4, "mut", tracking=0.06)
    pg.text(start + kw_w + 6, y, KEYWORDS, "I", 9.2, "mut")

    y += 12
    pg.hline(X0, X1, y, t["rule"], 0.7)

    # ---- 1 Introduction
    y += 22
    sec_head(pg, y, "1", "Introduction")
    y += 17
    y = pg.para(X0, y, W - 2 * X0, INTRO, 10.0, 13.8)

    # ---- 2 Selected work
    y += 24
    sec_head(pg, y, "2", "Selected Work")
    y += 17
    y = pg.para(X0, y, W - 2 * X0, SEC2, 10.0, 13.8)

    # ---- table
    y += 20
    y = table(pg, y)

    # ---- 3 Availability
    y += 32
    sec_head(pg, y, "3", "Availability")
    y += 17
    y = pg.para(X0, y, W - 2 * X0, SEC3, 10.0, 13.8)

    # ---- footer
    y += 24
    pg.hline(X0, X1, y, t["rule"], 0.7)
    y += 14
    pg.text(X0, y, "Correspondence: contact.samirpaudel@gmail.com", "T", 7.8, "mut")
    pg.text(X1, y, "Compiled 2026.11", "T", 7.8, "mut", anchor="end")
    y += 16
    pg.text(W / 2, y, "1", "R", 9.0, "mut", anchor="middle")

    return pg.finish(y + 26), y + 26


def sec_head(pg, y, num, title):
    pg.text(X0, y, num, "B", 11.5, "acc")
    pg.text(X0 + tw(num, "B", 11.5) + 10, y, title, "B", 11.5, "ink")


COL = {"num": 96, "dot": 104, "sys": 112, "con": 282, "sta": X1}
PAPER_ROW_H = 17.4


def table(pg, y):
    t = pg.t
    num, dot, sys, con, sta = COL["num"], COL["dot"], COL["sys"], COL["con"], COL["sta"]
    con_w = sta - 158 - con

    # caption above, as in a booktabs table
    pg.text(X0, y, "Table 1.", "B", 9.0, "ink")
    cap_x = X0 + tw("Table 1.", "B", 9.0) + 5
    pg.text(cap_x, y, "Systems included in this report, grouped by problem area.",
            "I", 9.0, "mut")
    y += 10

    pg.hline(X0, X1, y, t["rule"], 1.1)
    y += 12
    pg.smallcaps(num, y, "No.", 7.4, "mut", anchor="end", tracking=0.1)
    pg.smallcaps(sys, y, "System", 7.4, "mut", tracking=0.1)
    pg.smallcaps(con, y, "Contribution", 7.4, "mut", tracking=0.1)
    pg.smallcaps(sta, y, "Stack", 7.4, "mut", anchor="end", tracking=0.1)
    y += 5
    pg.hline(X0, X1, y, t["rule"], 0.6)

    i = 0
    for gi, (title, cards) in enumerate(SECTIONS):
        if gi:
            pg.hline(X0, X1, y + 5.6, t["faint"], 0.6)
        y += 12
        pg.text(sys, y, GROUP_LABEL.get(title, title), "I", 8.8, "mut")
        for card in cards:
            i += 1
            y += PAPER_ROW_H
            pg.text(num, y, f"{i:02d}", "T", 7.8, "mut", anchor="end")
            if card.get("live"):
                pg.parts.append(f'<circle cx="{dot}" cy="{y - 2.6:.1f}" r="2.1" '
                                f'fill="{t["acc"]}"/>')
            name = trunc(SYSTEM_NAME.get(card["name"], card["disp"].title()), "B", 9.8,
                         con - sys - 12)
            pg.text(sys, y, name, "B", 9.8, "ink")
            contrib = trunc(CONTRIBUTION.get(card["name"], card["desc"]), "R", 9.4, con_w)
            pg.text(con, y, contrib, "R", 9.4, "ink")
            stack = trunc(card["stack"], "T", 7.9, sta - (sta - 150))
            pg.text(sta, y, stack, "T", 7.9, "mut", anchor="end")
    y += 8
    pg.hline(X0, X1, y, t["rule"], 1.1)
    return y


# ------------------------------------------------- two-column table page --

def two_col_table(theme):
    pg = Page(theme)
    t = pg.t
    gutter = 56
    col_w = (X1 - X0 - gutter) / 2
    cols = [(X0, X0 + col_w), (X0 + col_w + gutter, X1)]

    # balance by rows: first four groups (13 rows) left, last two (12) right
    left = SECTIONS[:4]
    right = SECTIONS[4:]

    top = 40
    pg.smallcaps(X0, top, "Samir Paudel", 9.4, "ink", tracking=0.16)
    pg.text(X1, top, "SELECTED WORK · 2026.11", "T", 7.8, "mut", anchor="end")
    pg.hline(X0, X1, top + 11, t["rule"], 1.0)

    idx = [0]

    def column(x0, x1, groups, y):
        for gi, (title, cards) in enumerate(groups):
            if gi:
                y += 16
            pg.text(x0, y, GROUP_LABEL.get(title, title), "B", 14.0, "ink")
            pg.text(x1, y, str(len(cards)), "T", 7.6, "mut", anchor="end")
            y += 6
            pg.hline(x0, x1, y, t["rule"], 0.6)
            y += 14
            for card in cards:
                idx[0] += 1
                if card.get("live"):
                    pg.parts.append(f'<circle cx="{x0 + 3.6:.1f}" cy="{y - 3.1:.1f}" '
                                    f'r="2.0" fill="{t["acc"]}"/>')
                pg.text(x0 + 26, y, f"{idx[0]:02d}", "T", 7.4, "mut", anchor="end")
                name = trunc(SYSTEM_NAME.get(card["name"], card["disp"].title()),
                             "B", 10.4, col_w - 150)
                pg.text(x0 + 33, y, name, "B", 10.4, "ink")
                stack = trunc(card["stack"], "T", 7.5, 98)
                pg.text(x1, y, stack, "T", 7.5, "mut", anchor="end")
                contrib = trunc(CONTRIBUTION.get(card["name"], card["desc"]),
                                "R", 9.2, col_w - 33)
                pg.text(x0 + 33, y + 12.2, contrib, "R", 9.2, "mut")
                y += 28
        return y - 28 + 12.2

    y0 = 76
    left_bottom = column(cols[0][0], cols[0][1], left, y0)
    right_bottom = column(cols[1][0], cols[1][1], right, y0)

    # table note in the shorter (right) column
    if right_bottom < left_bottom - 24:
        rx0, rx1 = cols[1]
        ny = right_bottom + 20
        pg.hline(rx0, rx1, ny, t["faint"], 0.6)
        pg.parts.append(f'<circle cx="{rx0 + 3.4:.1f}" cy="{ny + 10.6:.1f}" '
                        f'r="2.0" fill="{t["acc"]}"/>')
        pg.text(rx0 + 12, ny + 14, "public demonstration", "I", 8.4, "mut")
        pg.text(rx0 + 12, ny + 26, "Numbers match the index below.", "I", 8.4, "mut")

    bottom = max(left_bottom, right_bottom)
    pg.hline(X0, X1, bottom + 20, t["rule"], 1.0)
    h = bottom + 44
    return pg.finish(h), h


# ------------------------------------------------- clickable table bands --

BW = 440                  # one half of the page
ROW_H, HEAD_H, LEGEND_H = 29, 32, 29
CW, CH = 880, 34          # caption strip
SIDES = {"left": (72, 420), "right": (20, 368)}


def table_items():
    """Split the sections into two columns of renderable lines."""
    left, right, idx = [], [], 0
    for gi, (title, cards) in enumerate(PORTFOLIO):
        side = left if gi < 3 else right
        side.append({"kind": "head", "title": title, "n": len(cards),
                     "label": f"{title} projects"})
        for card in cards:
            idx += 1
            side.append({"kind": "row", "card": card, "idx": idx,
                         "label": f"{idx:02d} {card['title']}"})
    return left, right


def caption_svg(theme):
    USED.clear()
    pg = Page(theme)
    t = pg.t
    pg.smallcaps(72, 15, "Samir Paudel", 9.6, "ink", tracking=0.16)
    pg.text(808, 15, "SELECTED WORK · 2026.11", "T", 7.8, "mut", anchor="end")
    pg.hline(72, 808, 24, t["rule"], 1.0)
    return pg.finish(CH, width=CW, frame=False,
                     label="Samir Paudel — selected work, 2026")


def block_svg(theme, side, item):
    USED.clear()
    pg = Page(theme)
    t = pg.t
    x0, x1 = SIDES[side]

    if item["kind"] == "head":
        pg.text(x0, 20.5, item["title"], "B", 15.0, "ink")
        pg.text(x1, 20.5, str(item["n"]), "T", 7.8, "mut", anchor="end")
        pg.hline(x0, x1, 27, t["rule"], 0.7)
        height, label = HEAD_H, item["title"]
    elif item["kind"] == "legend":
        pg.hline(x0, x1, 3, t["faint"], 0.6)
        pg.parts.append(f'<circle cx="{x0 + 3.4:.1f}" cy="14.2" r="2.0" '
                        f'fill="{t["acc"]}"/>')
        pg.text(x0 + 12, 17.4, "public demonstration", "I", 9.0, "mut")
        pg.text(x1, 17.4, "click any row for source", "I", 8.2, "mut",
                anchor="end")
        height, label = LEGEND_H, "public demonstration legend"
    else:
        card, idx = item["card"], item["idx"]
        if card["live"]:
            pg.parts.append(f'<circle cx="{x0 + 3.6:.1f}" cy="9.6" r="2.0" '
                            f'fill="{t["acc"]}"/>')
        pg.text(x0 + 26, 12.4, f"{idx:02d}", "T", 7.4, "mut", anchor="end")
        stack = trunc(card["stack"], "T", 7.5, 112)
        name = trunc(card["title"], "B", 10.4,
                     x1 - (x0 + 33) - tw(stack, "T", 7.5) - 14)
        pg.text(x0 + 33, 12.4, name, "B", 10.4, "ink")
        pg.text(x1, 12.4, stack, "T", 7.5, "mut", anchor="end")
        contrib = trunc(card["desc"], "R", 9.0, x1 - (x0 + 33))
        pg.text(x0 + 33, 24.2, contrib, "R", 9.0, "mut")
        height, label = ROW_H, f"{idx:02d} {card['title']}"

    return pg.finish(height, width=BW, frame=False, label=label)


# ----------------------------------------------------------------- build --

RAW = f"https://raw.githubusercontent.com/{USER}/{USER}/main/profile/cards-paper"
REPO = f"https://github.com/{USER}"


def ref_index():
    out, i = [], 0
    for _title, cards in SECTIONS:
        for card in cards:
            i += 1
            url = card.get("url", f"{REPO}/{card['name']}")
            label = SYSTEM_NAME.get(card["name"], card["disp"].title())
            out.append(f'[{i:02d}] <a href="{url}">{hesc(label)}</a>')
    return "<sub>" + " · ".join(out) + "</sub>"


def main():
    outdir = os.path.join(HERE, "cards-paper")
    os.makedirs(outdir, exist_ok=True)
    os.makedirs(os.path.join(outdir, "bands"), exist_ok=True)

    # ---- clickable bands: one image per line, wrapped in its own link
    bdir = os.path.join(outdir, "bands")
    os.makedirs(bdir, exist_ok=True)
    left_items, right_items = table_items()

    def write_band(stem, item, theme):
        svg2 = block_svg(theme, "left" if stem.startswith("l") else "right", item)
        with open(os.path.join(bdir, f"{stem}-{theme}.svg"), "w") as f:
            f.write(svg2)
        import xml.dom.minidom
        xml.dom.minidom.parseString(svg2)

    with open(os.path.join(bdir, "blank.svg"), "w") as f:
        f.write('<svg xmlns="http://www.w3.org/2000/svg" width="440" height="29" '
                'viewBox="0 0 440 29"></svg>')
    for theme in THEMES:
        with open(os.path.join(bdir, f"caption-{theme}.svg"), "w") as f:
            f.write(caption_svg(theme))
        for i, item in enumerate(left_items, 1):
            write_band(f"l{i:02d}", item, theme)
        for i, item in enumerate(right_items, 1):
            write_band(f"r{i:02d}", item, theme)

    rel = "profile/cards-paper/bands"

    def band_pic(stem, alt, width="49.5%"):
        return (f'<picture><source media="(prefers-color-scheme: dark)" '
                f'srcset="{rel}/{stem}-dark.svg"><img src="{rel}/{stem}-light.svg" '
                f'width="{width}" align="top" alt="{hesc(alt)}"></picture>')

    def band_link(item, stem):
        pic = band_pic(stem, item.get("label") or item["title"])
        if item["kind"] != "row":
            return pic
        card = item["card"]
        url = card.get("url") or f"{REPO}/{card.get('name', '')}"
        return f'<a href="{hesc(url)}">{pic}</a>'

    top = (f'<div align="center"><sub>'
           f'<a href="https://{USER}.github.io">website/wiki</a> · '
           f'<a href="https://x.com/{USER}">X</a> · '
           f'<a href="https://linkedin.com/in/{USER}">linkedin</a> · '
           f'<a href="mailto:contact.{USER}@gmail.com">email</a>'
           f'</sub></div>\n\n'
           f'<div align="center">')
    html_lines = [top,
                  band_pic("caption", "Samir Paudel — selected work · 2026.11",
                           "100%") + "<br>"]
    blank = (f'<picture><img src="{rel}/blank.svg" width="49.5%" '
             f'align="top" alt=""></picture>')
    for i in range(len(left_items)):
        cells = [band_link(left_items[i], f"l{i + 1:02d}")]
        if i < len(right_items):
            cells.append(band_link(right_items[i], f"r{i + 1:02d}"))
        else:
            cells.append(blank)
        html_lines.append("".join(cells) + "<br>")
    html_lines.append("</div>")

    bands_md = ("<!-- Generated by profile/build_paper.py: edit that and rebuild, "
                "not this file. -->\n\n" + "\n".join(html_lines) + "\n")
    with open(os.path.join(ROOT, "README.bands.md"), "w") as f:
        f.write(bands_md)

    for theme in THEMES:
        css = "gh-md-light.css" if theme == "light" else "gh-md-dark.css"
        html = f"""<!doctype html><meta charset="utf-8"><title>bands {theme}</title>
<link rel="stylesheet" href="../{css}">
<style>
 html {{ background:{THEMES[theme]["bg"]}; }}
 body {{ margin:0; padding:32px 0 64px; }}
 .markdown-body {{ max-width:980px; margin:0 auto; padding:0 45px;
                   background:transparent; }}
 .markdown-body a {{ text-decoration:none; }}
</style>
<article class="markdown-body">
{bands_md}
</article>
"""
        with open(os.path.join(ROOT, f"preview-bands-{theme}.html"), "w") as f:
            f.write(html)

    print(f"bands: {len(left_items)}+{len(right_items)} blocks")


if __name__ == "__main__":
    main()
