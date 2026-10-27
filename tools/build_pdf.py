"""Build the offline PDF copy of the handbook from preview/index.html.

Agenda data (PLACES / DAYS / EVENTS) is read from the page's own script via
tools/extract_data.sh, and the Info tab is taken from the page's HTML, so the
PDF always matches the web version.

Usage:  tools/extract_data.sh && python3 tools/build_pdf.py
"""
import json
import re
from pathlib import Path

import fitz  # PyMuPDF

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "preview" / "index.html"
DATA = ROOT / "tools" / "data.json"
OUT = ROOT / "preview" / "Xiamen-2027-Handbook.pdf"
FONTS = ROOT / "tools" / "fonts"

W, H, M = 360, 640, 24          # phone-shaped page (9:16), in points
SEA, SUN, MUTED = "#14324a", "#f08a4b", "#6b7a86"

EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿⬀-⯿️]")


def clean(s):
    return EMOJI.sub("", s).strip()


def esc(s):
    return clean(str(s)).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


CSS = f"""
@font-face {{ font-family: body; src: url(hira-w3.otf); }}
@font-face {{ font-family: body; font-weight: bold; src: url(hira-w6.otf); }}
@font-face {{ font-family: head; src: url(songti-bold.ttf); }}
* {{ font-family: body; }}
body {{ font-size: 9.5pt; line-height: 1.45; color: #1b2a36; }}
h1 {{ font-family: head; font-size: 30pt; color: {SEA}; margin: 0; }}
h2 {{ font-family: head; font-size: 17pt; color: {SEA}; margin: 14pt 0 6pt 0; }}
h3 {{ font-family: head; font-size: 13pt; color: {SEA}; margin: 12pt 0 4pt 0; }}
h4 {{ font-size: 10pt; margin: 8pt 0 2pt 0; }}
p {{ margin: 2pt 0; }}
.eyebrow {{ font-size: 9pt; color: {SUN}; font-weight: bold; letter-spacing: 1pt; }}
.sub {{ font-family: head; font-size: 15pt; color: {SEA}; }}
.muted {{ color: {MUTED}; font-size: 8.5pt; }}
.day {{ font-family: head; font-size: 14pt; color: {SEA}; margin: 12pt 0 2pt 0; }}
.item {{ margin: 6pt 0 0 0; padding: 0 0 6pt 0; border-bottom: 0.5pt solid #e6ddcf; }}
.t {{ color: #1f4a68; font-weight: bold; }}
.tag {{ color: {SUN}; font-size: 7.5pt; font-weight: bold; }}
.zh {{ font-size: 10pt; }}
.box {{ border: 0.8pt solid #d9cfbf; padding: 5pt; margin: 4pt 0; }}
.note {{ font-size: 8.5pt; color: {MUTED}; }}
ol, ul {{ margin: 2pt 0 2pt 0; padding-left: 14pt; }}
li {{ margin: 2pt 0; }}
"""


def place_html(p):
    out = [f'<p><b>{esc(p["name"])}</b></p>']
    if p.get("addrZh"):
        out.append(f'<p class="zh">{esc(p["addrZh"])}</p>')
    if p.get("addrEn"):
        out.append(f'<p class="muted">{esc(p["addrEn"])}</p>')
    if p.get("transport"):
        out.append(f'<p class="muted">{esc(p["transport"])}</p>')
    if p.get("copyLabel"):
        out.append(f'<p class="muted">DiDi destination: <b>{esc(p.get("copyName") or p["zh"])}</b></p>')
    return "".join(out)


CROPS = Path(__file__).resolve().parent / ".crops"


def day_photo(d, n):
    """Wide 16:9 crop of the day's team-activity photo (hotel courtyard on check-out day)."""
    from PIL import Image
    team = [e for e in d["EVENTS"] if e["day"] == n and e.get("kind") == "team" and e.get("place")]
    photos = d["PLACES"][team[0]["place"]].get("photos") if team else ["img/hotel-courtyard.jpg"]
    if not photos:
        return None
    CROPS.mkdir(exist_ok=True)
    im = Image.open(ROOT / "preview" / photos[0]).convert("RGB")
    w, h = im.size
    ch = min(h, int(w * 9 / 16)); cw = min(w, int(ch * 16 / 9))
    top = (h - ch) // 2
    name = f"day{n}.jpg"
    im.crop(((w - cw) // 2, top, (w - cw) // 2 + cw, top + ch)).resize((800, 450)).save(CROPS / name, quality=72)
    return name


def agenda_pages(d):
    """One HTML chunk per day, so each day starts on its own page."""
    tags = {"team": "TEAM", "logi": "LOGISTICS", "otot": "OTOT"}
    pages = []
    for day in d["DAYS"]:
        theme = f' · {esc(day["theme"])}' if day.get("theme") else ""
        parts = [f'<p class="eyebrow">AGENDA</p><h2 style="margin-top:2pt">Day {day["n"]}</h2><p class="muted">{esc(day["label"])}{theme}</p>']
        photo = day_photo(d, day["n"])
        if photo:
            parts.append(f'<p style="margin:6pt 0 4pt 0"><img src="{photo}" width="{W - 2 * M}"></p>')
        for e in [e for e in d["EVENTS"] if e["day"] == day["n"] and not e.get("tba")]:
            parts.append('<div class="item">')
            parts.append(f'<p class="tag">{tags[e["kind"]]}</p>')
            parts.append(f'<p><span class="t">{esc(e["timeLabel"])}</span> &nbsp;<b>{esc(e["title"])}</b></p>')
            for k in ("sub", "extra", "note"):
                if e.get(k):
                    parts.append(f'<p class="note">{esc(e[k])}</p>')
            if e.get("place"):
                parts.append(place_html(d["PLACES"][e["place"]]))
            parts.append("</div>")
        pages.append("".join(parts))
    return pages


def info_html():
    h = PAGE.read_text()
    a = h.index('<section id="tab-info"')
    sec = h[a:h.index("</section>", a)]
    sec = re.sub(r'<div class="btns".*?</div>', "", sec, flags=re.S)       # copy / driver buttons
    sec = re.sub(r'<div id="infoStrip"></div>', "", sec)
    sec = re.sub(r'<div class="wx".*?</div>', '<p class="muted">Xiamen in January is usually 10–18°C and breezy by the sea. Bring appropriate clothing.</p>', sec, flags=re.S)
    # checklist -> plain lines with an empty box, detail text on its own line
    sec = re.sub(r'<ul class="check"[^>]*>(.*?)</ul>', lambda m: re.sub(r"<li>(.*?)</li>", r"<p>\1</p>", m.group(1), flags=re.S), sec, flags=re.S)
    sec = re.sub(r'<input[^>]*>', "&#9633; ", sec)
    sec = re.sub(r'<label[^>]*>', "", sec).replace("</label>", "")
    sec = re.sub(r'(<p>&#9633;[^<]*)\s*<small>', r"\1<br><small>", sec)
    sec = re.sub(r'<a [^>]*href="tel:[^"]*"[^>]*>(.*?)</a>', lambda m: "<p>" + m.group(1).replace("</b><small>", "</b> &nbsp;<small>") + "</p>", sec, flags=re.S)
    sec = re.sub(r'<a [^>]*href="(http[^"]*)"[^>]*>.*?</a>', r"\1", sec, flags=re.S)
    sec = re.sub(r"<small>(.*?)</small>", r'<span class="muted">\1</span>', sec, flags=re.S)
    sec = re.sub(r"<dt>(.*?)</dt><dd>(.*?)</dd>", r"<p><b>\1</b> &nbsp;\2</p>", sec, flags=re.S)
    sec = re.sub(r'<div class="addrbox">(.*?)</div>', r'<div class="box">\1</div>', sec, flags=re.S)
    sec = re.sub(r"<b>(.*?)</b>(?=[^<])", r"<b>\1</b><br>", sec)              # scam title on its own line
    # drop the "Save offline" card: not relevant inside the PDF
    sec = sec[:sec.index('<div class="icard">\n      <h3>📲 Save offline</h3>')]
    sec = sec[sec.index(">") + 1:]
    return "<h2>Handy Info</h2>" + EMOJI.sub("", sec)


def cover_html():
    return f"""
    <p class="eyebrow">EXO TEAM RETREAT 2027</p>
    <h1>Xiamen</h1>
    <p class="sub">厦门 · Amoy</p>
    <p>Mon 11 – Thu 14 January 2027</p>
    <p style="margin-top:8pt"><img src="hotel-pool.jpg" width="{W - 2 * M}"></p>
    <p class="muted" style="margin-top:6pt">Offline copy of the handbook. The live version, with countdown, photos and weather:
    teamretreats.github.io/xiamen2027</p>
    """


def main():
    d = json.loads(DATA.read_text())
    sections = [cover_html(), *agenda_pages(d), info_html()]   # each section starts on a new page
    html = "".join(sections)
    # subset the fonts to just the characters used, so the PDF stays small
    import tempfile
    from fontTools import subset
    used = "".join(sorted(set(re.sub(r"<[^>]+>", "", html)))) + "0123456789/ "
    tmp = Path(tempfile.mkdtemp())
    for f in FONTS.iterdir():
        opts = subset.Options(); opts.name_IDs = ["*"]; opts.notdef_outline = True; opts.retain_gids = True
        font = subset.load_font(str(f), opts)
        sub = subset.Subsetter(opts); sub.populate(text=used); sub.subset(font)
        subset.save_font(font, str(tmp / f.name), opts)
    arch = fitz.Archive()
    arch.add(str(tmp))
    arch.add(str(ROOT / "preview" / "img"))
    arch.add(str(CROPS))
    writer = fitz.DocumentWriter(str(OUT))
    for sec in sections:
        story = fitz.Story(html=f"<body>{sec}</body>", user_css=CSS, archive=arch)
        more = True
        while more:
            dev = writer.begin_page(fitz.Rect(0, 0, W, H))
            more, _ = story.place(fitz.Rect(M, M, W - M, H - M))
            story.draw(dev)
            writer.end_page()
    writer.close()

    # page numbers
    doc = fitz.open(str(OUT))
    for i, page in enumerate(doc):
        page.insert_text((W - M - 30, H - 10), f"{i + 1} / {doc.page_count}", fontsize=7, color=(0.42, 0.48, 0.53))
    doc.save(str(OUT) + ".tmp", garbage=4, deflate=True)
    doc.close()
    Path(str(OUT) + ".tmp").replace(OUT)
    print(f"{OUT.name}: {OUT.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
