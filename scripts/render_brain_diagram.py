"""Render the README overview from the same graph data as the interactive atlas."""

# ruff: noqa: E501 -- complete SVG elements keep the rendering template readable.
import argparse
import json
from html import escape
from pathlib import Path
from xml.etree import ElementTree as ET

root = Path(__file__).resolve().parents[1]
flow = json.loads((root / "docs/assets/brain-flow.json").read_text())
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--lang", choices=["en", "zh-CN"], default="en")
args = parser.parse_args()
locale = json.loads((root / "docs/assets/brain-flow.zh-CN.json").read_text())
view = flow["views"][0]
if args.lang == "zh-CN":
    translated = locale["views"][view["id"]]
    view = {**view, "nodes": [{**node, **translated["nodes"][node["id"]]} for node in view["nodes"]]}


def translate(text):
    return locale["ui"].get(text, text) if args.lang == "zh-CN" else text

parts = ['''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="870" viewBox="0 0 1200 870" role="img" aria-labelledby="title desc">
<title id="title">Companion brain: semantic memory, episodic memory, consolidation and emotion</title>
<desc id="desc">A turn retrieves scoped evidence, facts, episodes and character state. The model replies, validates and commits. Cited consolidation derives episodes and core notes; bounded emotional state feeds the next turn. Evidence uses RRF; archive ranking uses relevance, recency and importance.</desc>
<rect width="1200" height="870" rx="18" fill="#f7f5ee"/>
<style>text{font-family:Arial,"PingFang SC","Microsoft YaHei","Noto Sans CJK SC",sans-serif}.tag{font-size:8px;letter-spacing:.65px}.title{font-size:14px;font-weight:600;fill:#2e3926}.sub{font-size:9.5px;fill:#59614d}</style>
<text x="30" y="35" font-size="10" letter-spacing="2" fill="#805239">ANIMA LAB / THE BRAIN ATLAS</text>
<text x="30" y="79" font-size="32" fill="#35422b">A moment becomes continuity.</text>
<text x="30" y="108" font-size="13" fill="#57604c">Original evidence. Semantic facts. Episodic accounts. A character state that evolves.</text>
<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0 0L10 5L0 10" fill="#898e79"/></marker></defs>
<g transform="translate(0,130)">''']
for edge in view["edges"]:
    parts.append(f'<path d="{edge["d"]}" fill="none" stroke="#b2b7a2" stroke-width="1.7" marker-end="url(#arrow)"/>')
colors = {"neutral": ("#fffdf7", "#b9b3a3", "#4c5343"), "memory": ("#f0f2e8", "#a5af91", "#44573c"), "emotion": ("#f8eee5", "#c0a28e", "#895335")}
for n in view["nodes"]:
    x, y = n["x"], n["y"]
    fill, stroke, ink = colors[n["tone"]]
    parts.append(f'<rect x="{x}" y="{y}" width="{n["w"]}" height="{n["h"]}" rx="11" fill="{fill}" stroke="{stroke}"/>')
    for key, dy, cls in [("tag", 23, "tag"), ("title", 51, "title"), ("subtitle", 76, "sub")]:
        parts.append(f'<text x="{x+16}" y="{y+dy}" class="{cls}" fill="{ink}">{escape(n[key])}</text>')
for y, text in [(45, "THE CONVERSATION"), (278, "MEMORY / EVERY DERIVED RECORD KEEPS ITS SOURCES"), (489, "CONTINUITY LOOPS")]:
    parts.append(f'<text x="30" y="{y}" font-size="9" letter-spacing="1.4" fill="#626953">{escape(translate(text))}</text>')
parts.append('''</g><path d="M30 795H1170" stroke="#d5d1c2"/>
<text x="30" y="822" font-size="12" fill="#4b5740">Evidence: Σ 1/(40 + rank). Archive: 0.6 relevance + 0.25 recency + 0.15 importance. Open loops: arousal + urgency.</text>
<text x="30" y="847" font-size="11" fill="#626953">Explore four interactive views for exact formulas, cited consolidation and PAD / relationship decay. Optional features depend on configuration.</text></svg>''')
# Translate only authored text, never coordinates, identifiers or formulas.
ET.register_namespace("", "http://www.w3.org/2000/svg")
svg = ET.fromstring("\n".join(parts))
svg.set("lang", args.lang)
for element in svg.iter():
    if element.tag.rsplit("}", 1)[-1] in {"text", "title", "desc"} and element.text:
        element.text = translate(element.text)
if args.lang == "zh-CN":
    style = svg.find("{http://www.w3.org/2000/svg}style")
    style.text += ".tag{font-size:9px}.title{font-size:15px}.sub{font-size:11px}"
suffix = ".zh-CN" if args.lang == "zh-CN" else ""
target = root / f"docs/assets/brain-flow{suffix}.svg"
target.write_text(ET.tostring(svg, encoding="unicode") + "\n")
print(target.relative_to(root))
