#!/usr/bin/env python3
"""Snapshot the portfolio's projects into profile/portfolio.py.

Reads the Jekyll site's `_data/projects.yml` (featured cards) plus the
hard-coded "Others" table in `_home/projects.md`, and writes the vendored
list used by `build_paper.py`. Re-run this after editing the portfolio.

  python3 profile/sync_portfolio.py [path-to-paumelsamir.github.io]
"""

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SITE = "/home/sam/Work/paudelsamir.github.io"

# order and headings follow _home/projects.md
GROUPS = [
    ("fullstack", "Full-stack AI"),
    ("aiml", "AI/ML and deep learning"),
    ("collections", "Collections"),
    ("omarchy", "Linux"),
    ("more", "Miscellaneous"),
]

# the author's tags are sometimes generic; keep the table's one-liner column tight
STACK_OVERRIDE = {
    "Cat vs Dog Classifier": "cnn · vision",
    "Guess The Footballer": "cnn · vision",
    "Image Captioning": "cnn · transformer",
    "GPT from Scratch": "transformers · llm",
    "Player Value Prediction": "regression · python",
    "Movie Recommender": "recommender · python",
    "30DaysOfData-LearningUtsav": "python · data",
    "chesssense": "chess engine",
    "mini-compiler": "lexer · parser",
    "Movie-Recommender-System": "tf-idf · streamlit",
    "toneclone": "discord bot",
}


def read_yaml(path):
    out = subprocess.run(
        ["ruby", "-ryaml", "-rjson", "-e",
         'puts JSON.generate(YAML.load_file(ARGV[0]))', path],
        check=True, capture_output=True, text=True,
    )
    return json.loads(out.stdout)


def stack_for(project):
    title = project["title"]
    if title in STACK_OVERRIDE:
        return STACK_OVERRIDE[title]
    tags = [t for t in (project.get("tags") or [])
            if t.strip().lower() != "omarchy"]
    return " · ".join(t.strip().lower() for t in tags)


FEATURED = {
    # Full-stack AI: all
    "personal wiki", "meantrainer", "nyayak",
    # AI/ML
    "player value prediction", "movie recommender", "guess the footballer",
    "choose your own adventure", "image captioning", "formation tracker",
    # Collections
    "365 days of data", "coding interview prep",
    # Linux
    "switcher", "news dash", "agebar", "wayfarer", "guitar", "notch island",
    # Miscellaneous
    "toneclone", "chesssense",
}

def card(project):
    demo, code = project.get("demo"), project.get("code")
    project_live = project["title"].strip().lower() in FEATURED
    project_url = demo or code or ""
    return {
        "title": project["title"],
        "desc": project.get("description", ""),
        "stack": stack_for(project),
        "url": project_url,
        "live": project_live,
    }


def others(path):
    text = open(path).read()
    text = text[text.index("## Others"):]
    out = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", text, re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        if len(cells) < 4:
            continue
        title = re.sub(r"<[^>]+>", "", cells[0]).strip()
        category = re.sub(r"<[^>]+>", "", cells[1]).strip().lower()
        desc = re.sub(r"<[^>]+>", "", cells[2]).strip()
        links = re.findall(r'href="([^"]+)"', cells[3])
        demo = next((u for u, label in zip(links, re.findall(r">([^<]+)</a>", cells[3]))
                     if label.strip() == "demo"), None)
        out.append({
            "title": title,
            "desc": desc,
            "stack": category,
            "url": demo or (links[0] if links else ""),
            "live": bool(demo),
        })
    return out


def pyval(v):
    if isinstance(v, bool):
        return "True" if v else "False"
    return json.dumps(v, ensure_ascii=False)


def pretty(obj):
    def fmt(value, indent):
        pad = " " * indent
        if isinstance(value, str):
            return json.dumps(value, ensure_ascii=False)
        if isinstance(value, dict):
            body = ",\n".join(
                f"{pad}    {json.dumps(k, ensure_ascii=False)}: {fmt(v, indent + 4)}"
                for k, v in value.items())
            return "{\n" + body + f",\n{pad}}}"
        raise TypeError(type(value))
    return fmt(obj, 0)


def main():
    site = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SITE
    data = read_yaml(os.path.join(site, "_data", "projects.yml"))
    groups = [(label, [card(p) for p in data[key]]) for key, label in GROUPS]

    # Personal Wiki (not part of the portfolio cards, but lives on the profile)
    wiki = {
        "title": "Personal Wiki",
        "desc": "Private RAG over notes and resumes.",
        "stack": "rag · llm · memory",
        "url": "https://github.com/paudelsamir/wiki",
        "live": True,
    }
    for i, (label, cards) in enumerate(groups):
        if label == "Full-stack AI":
            groups[i] = (label, [wiki] + cards)
            break

    lines = [
        '"""Projects shown on paudelsamir.github.io — generated, do not edit.',
        "",
        "Regenerate with: python3 profile/sync_portfolio.py [site-path]",
        '"""',
        "",
        "PORTFOLIO = [",
    ]
    for label, cards in groups:
        lines.append(f"    ({json.dumps(label, ensure_ascii=False)}, [")
        for c in cards:
            lines.append("        {")
            for k, v in c.items():
                lines.append(f"            {json.dumps(k)}: {pyval(v)},")
            lines.append("        },")
        lines.append("    ]),")
    lines.append("]")
    out = os.path.join(HERE, "portfolio.py")
    open(out, "w").write("\n".join(lines) + "\n")
    total = sum(len(c) for _l, c in groups)
    print(f"wrote {out}: {len(groups)} groups, {total} projects")


if __name__ == "__main__":
    main()
