#!/usr/bin/env python3
"""
build.py — programmatic SEO generator for a Laravel developer site.

Reads data/keywords.json and writes static HTML pages, an index, and a sitemap
into output/. No external dependencies — runs anywhere Python 3 runs.

    python3 build.py
"""

import json, html, datetime, pathlib, re

ROOT = pathlib.Path(__file__).parent
DATA = json.loads((ROOT / "data" / "keywords.json").read_text(encoding="utf-8"))
TEMPLATE = (ROOT / "templates" / "page.html").read_text(encoding="utf-8")
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)

SITE = DATA["site"]
AFFILIATES = DATA["affiliates"]
YEAR = datetime.date.today().year
TODAY = datetime.date.today().isoformat()

TYPE_LABELS = {
    "deploy": "Deployment guide",
    "fix": "Fix / troubleshooting",
    "compare": "Comparison",
    "howto": "How-to guide",
}

def esc(s): return html.escape(str(s), quote=True)

def slugify(text):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return re.sub(r"-+", "-", s)

# ---------- block rendering ----------

def render_blocks(blocks):
    out = []
    for b in blocks:
        t = b["type"]
        if t == "h2":
            out.append(f"<h2>{esc(b['text'])}</h2>")
        elif t == "p":
            out.append(f"<p>{esc(b['text'])}</p>")
        elif t == "ul":
            items = "".join(f"<li>{esc(i)}</li>" for i in b["items"])
            out.append(f"<ul>{items}</ul>")
        elif t == "code":
            lang = esc(b.get("lang", ""))
            label = f'<span class="lang">{lang}</span>' if lang else ""
            out.append(f'<pre>{label}<code>{esc(b["text"])}</code></pre>')
    return "\n    ".join(out)

def render_ad(aff_key):
    a = AFFILIATES.get(aff_key)
    if not a:
        return ""
    return f"""<div class="ad">
      <div class="tag">Recommended hosting</div>
      <div class="name">{esc(a['name'])}</div>
      <p>{esc(a['blurb'])}</p>
      <a class="btn" href="{esc(a['url'])}" rel="sponsored nofollow" target="_blank">{esc(a['cta'])}</a>
      <p class="disc">Affiliate link — we may earn a commission at no extra cost to you.</p>
    </div>"""

def render_faq(faq):
    if not faq:
        return ""
    rows = []
    for item in faq:
        rows.append(f'<div class="q">{esc(item["q"])}</div><p class="a">{esc(item["a"])}</p>')
    return '<div class="faq"><h2>Frequently asked questions</h2>' + "".join(rows) + "</div>"

def render_related(slugs, lookup):
    if not slugs:
        return ""
    links = []
    for s in slugs:
        title = lookup.get(s, s)
        links.append(f'<a href="{esc(s)}.html"><span>→</span>{esc(title)}</a>')
    return ('<div class="related"><div class="eyebrow">Related</div>'
            + "".join(links) + "</div>")

# ---------- structured data ----------

def jsonld(page):
    canonical = f"{SITE['base_url']}/{page['slug']}.html"
    article = {
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "headline": page["h1"],
        "description": page["meta_description"],
        "datePublished": page.get("updated", TODAY),
        "dateModified": page.get("updated", TODAY),
        "author": {"@type": "Organization", "name": SITE["author"]},
        "mainEntityOfPage": canonical,
    }
    graph = [article]
    if page.get("faq"):
        graph.append({
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": q["q"],
                 "acceptedAnswer": {"@type": "Answer", "text": q["a"]}}
                for q in page["faq"]
            ],
        })
    blob = json.dumps(graph, ensure_ascii=False, indent=2)
    return f'<script type="application/ld+json">\n{blob}\n</script>'

# ---------- page assembly ----------

def build_page(page, lookup):
    canonical = f"{SITE['base_url']}/{page['slug']}.html"
    name = SITE["name"]
    # split logo into prefix + accented suffix (last capitalized chunk)
    m = re.match(r"(.*?)([A-Z][a-z]+)$", name)
    prefix, suffix = (m.group(1), m.group(2)) if m else (name, "")

    draft = ""
    if page.get("_draft"):
        draft = ('<div class="draft">DRAFT — generated skeleton. '
                 'Fill the body before publishing (run generate_content.py or write by hand).</div>')

    repl = {
        "{{LANG}}": SITE["lang"],
        "{{TITLE}}": esc(page["title"]),
        "{{META_DESCRIPTION}}": esc(page["meta_description"]),
        "{{CANONICAL}}": esc(canonical),
        "{{JSONLD}}": jsonld(page),
        "{{SITE_PREFIX}}": esc(prefix),
        "{{SITE_SUFFIX}}": esc(suffix),
        "{{SITE_NAME}}": esc(name),
        "{{TAGLINE}}": esc(SITE["tagline"]),
        "{{TYPE}}": esc(page["type"]),
        "{{TYPE_LABEL}}": esc(TYPE_LABELS.get(page["type"], page["type"])),
        "{{SLUG}}": esc(page["slug"]),
        "{{H1}}": esc(page["h1"]),
        "{{DRAFT_NOTICE}}": draft,
        "{{INTRO}}": esc(page["intro"]),
        "{{UPDATED}}": esc(page.get("updated", TODAY)),
        "{{AUTHOR}}": esc(SITE["author"]),
        "{{BODY}}": render_blocks(page.get("blocks", [])),
        "{{AD}}": render_ad(page.get("affiliate")),
        "{{FAQ}}": render_faq(page.get("faq", [])),
        "{{RELATED}}": render_related(page.get("related", []), lookup),
        "{{YEAR}}": str(YEAR),
    }
    out = TEMPLATE
    for k, v in repl.items():
        out = out.replace(k, v)
    (OUT / f"{page['slug']}.html").write_text(out, encoding="utf-8")

# ---------- matrix expansion ----------

def expand_matrix():
    mx = DATA.get("matrix")
    if not mx:
        return []
    pages = []
    for tpl in mx["templates"]:
        source = mx["tasks"] if tpl["type"] == "howto" else mx["errors"]
        key = "task" if tpl["type"] == "howto" else "error"
        for value in source:
            vslug = slugify(value)
            slug = tpl["pattern"].format(**{f"{key}_slug": vslug})
            pages.append({
                "slug": slug,
                "type": tpl["type"],
                "h1": tpl["h1"].format(**{key: value}),
                "title": tpl["title"].format(**{key: value}),
                "meta_description": tpl["meta_description"].format(**{key: value}),
                "affiliate": tpl["affiliate"],
                "updated": TODAY,
                "intro": f"This guide covers {value} in Laravel. "
                         "Replace this with the real walkthrough before publishing.",
                "blocks": [
                    {"type": "h2", "text": "Steps"},
                    {"type": "p", "text": "TODO: write the actual steps with copy-paste code."},
                    {"type": "h2", "text": "Common mistakes"},
                    {"type": "p", "text": "TODO: list the errors people hit and how to avoid them."},
                ],
                "faq": [],
                "related": [],
                "_draft": True,
            })
    return pages

# ---------- index + sitemap ----------

def build_index(pages):
    groups = {}
    for p in pages:
        groups.setdefault(p["type"], []).append(p)
    sections = []
    for typ, label in TYPE_LABELS.items():
        if typ not in groups:
            continue
        links = "".join(
            f'<a href="{esc(p["slug"])}.html"><span>→</span>{esc(p["h1"])}'
            + (' <em style="color:#b08900;font-style:normal">· draft</em>' if p.get("_draft") else "")
            + "</a>"
            for p in groups[typ]
        )
        sections.append(f'<div class="related"><div class="eyebrow">{esc(label)}</div>{links}</div>')

    page = {
        "slug": "index", "type": "home",
        "h1": SITE["name"], "title": f"{SITE['name']} — {SITE['tagline']}",
        "meta_description": SITE["tagline"], "intro": SITE["tagline"],
        "blocks": [], "faq": [], "related": [], "affiliate": None,
    }
    # reuse template, drop the body into RELATED slot via sections
    lookup = {}
    html_out = TEMPLATE
    canonical = f"{SITE['base_url']}/index.html"
    m = re.match(r"(.*?)([A-Z][a-z]+)$", SITE["name"])
    prefix, suffix = (m.group(1), m.group(2)) if m else (SITE["name"], "")
    repl = {
        "{{LANG}}": SITE["lang"], "{{TITLE}}": esc(page["title"]),
        "{{META_DESCRIPTION}}": esc(page["meta_description"]),
        "{{CANONICAL}}": esc(canonical), "{{JSONLD}}": "",
        "{{SITE_PREFIX}}": esc(prefix), "{{SITE_SUFFIX}}": esc(suffix),
        "{{SITE_NAME}}": esc(SITE["name"]), "{{TAGLINE}}": esc(SITE["tagline"]),
        "{{TYPE}}": "home", "{{TYPE_LABEL}}": "Index", "{{SLUG}}": "",
        "{{H1}}": esc(page["h1"]), "{{DRAFT_NOTICE}}": "", "{{INTRO}}": esc(page["intro"]),
        "{{UPDATED}}": TODAY, "{{AUTHOR}}": esc(SITE["author"]),
        "{{BODY}}": "", "{{AD}}": "", "{{FAQ}}": "",
        "{{RELATED}}": "".join(sections), "{{YEAR}}": str(YEAR),
    }
    for k, v in repl.items():
        html_out = html_out.replace(k, v)
    (OUT / "index.html").write_text(html_out, encoding="utf-8")

def build_sitemap(pages):
    urls = [f"{SITE['base_url']}/index.html"] + [
        f"{SITE['base_url']}/{p['slug']}.html" for p in pages
    ]
    body = "".join(
        f"  <url><loc>{esc(u)}</loc><lastmod>{TODAY}</lastmod></url>\n" for u in urls
    )
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           f"{body}</urlset>\n")
    (OUT / "sitemap.xml").write_text(xml, encoding="utf-8")

# ---------- run ----------

def main():
    authored = DATA["pages"]
    matrix = expand_matrix()
    all_pages = authored + matrix
    lookup = {p["slug"]: p["h1"] for p in all_pages}

    for p in all_pages:
        build_page(p, lookup)
    build_index(all_pages)
    build_sitemap(all_pages)

    drafts = sum(1 for p in all_pages if p.get("_draft"))
    full = len(all_pages) - drafts
    print(f"[built] {len(all_pages)} pages -> {OUT}/")
    print(f"  - {full} full pages ready to publish")
    print(f"  - {drafts} skeleton pages need content before publishing")
    print(f"  - index.html + sitemap.xml generated")

if __name__ == "__main__":
    main()
