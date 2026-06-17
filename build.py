#!/usr/bin/env python3
"""
build.py — programmatic SEO generator for a Laravel developer site.

Reads data/keywords.json and writes static HTML pages, an index, and a sitemap
into output/. No external dependencies — runs anywhere Python 3 runs.

    python build.py        # (python3 on macOS/Linux)

Supports multiple languages: a page can set "lang" (e.g. "ar", "fr") and a
"group" key shared with its translations. Same-group pages get hreflang tags
and a language switcher automatically. Arabic pages render right-to-left.
"""

import json, html, datetime, pathlib, re

ROOT = pathlib.Path(__file__).parent
DATA = json.loads((ROOT / "data" / "keywords.json").read_text(encoding="utf-8"))
TEMPLATE = (ROOT / "templates" / "page.html").read_text(encoding="utf-8")
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)

SITE = DATA["site"]
AFFILIATES = DATA["affiliates"]
I18N = DATA.get("i18n", {})
DEFAULT_LANG = SITE["lang"]
YEAR = datetime.date.today().year
TODAY = datetime.date.today().isoformat()

LANG_LABELS = {"en": "English", "ar": "العربية", "fr": "Français"}

def esc(s): return html.escape(str(s), quote=True)

def slugify(text):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return re.sub(r"-+", "-", s)

def strings_for(lang):
    """UI strings for a language, falling back to the default language."""
    base = dict(I18N.get(DEFAULT_LANG, {}))
    base.update(I18N.get(lang, {}))
    tl = dict(I18N.get(DEFAULT_LANG, {}).get("type_labels", {}))
    tl.update(I18N.get(lang, {}).get("type_labels", {}))
    base["type_labels"] = tl
    return base

def page_lang(page): return page.get("lang", DEFAULT_LANG)
def page_dir(page):  return page.get("dir", "rtl" if page_lang(page) == "ar" else "ltr")

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
            # code is always LTR, even inside an RTL page
            out.append(f'<pre dir="ltr">{label}<code>{esc(b["text"])}</code></pre>')
    return "\n    ".join(out)

def render_ad(aff_key, lang, strings):
    a = AFFILIATES.get(aff_key)
    if not a:
        return ""
    blurb = a.get(f"blurb_{lang}", a["blurb"])
    cta = a.get(f"cta_{lang}", a["cta"])
    return f"""<div class="ad">
      <div class="tag">{esc(strings['ad_tag'])}</div>
      <div class="name">{esc(a['name'])}</div>
      <p>{esc(blurb)}</p>
      <a class="btn" href="{esc(a['url'])}" rel="sponsored nofollow" target="_blank">{esc(cta)}</a>
      <p class="disc">{esc(strings['disclosure'])}</p>
    </div>"""

def render_faq(faq, strings):
    if not faq:
        return ""
    rows = []
    for item in faq:
        rows.append(f'<div class="q">{esc(item["q"])}</div><p class="a">{esc(item["a"])}</p>')
    return f'<div class="faq"><h2>{esc(strings["faq"])}</h2>' + "".join(rows) + "</div>"

def render_related(slugs, lookup, strings):
    if not slugs:
        return ""
    links = []
    for s in slugs:
        title = lookup.get(s, s)
        links.append(f'<a href="{esc(s)}.html"><span>→</span>{esc(title)}</a>')
    return (f'<div class="related"><div class="eyebrow">{esc(strings["related"])}</div>'
            + "".join(links) + "</div>")

def render_langs(page, groups):
    """Language switcher linking a page to its translations in the same group."""
    g = page.get("group")
    if not g or g not in groups or len(groups[g]) < 2:
        return ""
    cur = page_lang(page)
    parts = []
    for lang in ["en", "ar", "fr"]:
        if lang not in groups[g]:
            continue
        label = LANG_LABELS.get(lang, lang)
        if lang == cur:
            parts.append(f"<strong>{esc(label)}</strong>")
        else:
            parts.append(f'<a href="{esc(groups[g][lang])}.html">{esc(label)}</a>')
    return '<div class="langs">' + " · ".join(parts) + "</div>"

# ---------- head extras ----------

def hreflang(page, groups):
    g = page.get("group")
    if not g or g not in groups:
        return ""
    base = SITE["base_url"]
    out = [f'<link rel="alternate" hreflang="{esc(lang)}" href="{esc(base)}/{esc(slug)}.html">'
           for lang, slug in groups[g].items()]
    if DEFAULT_LANG in groups[g]:
        out.append(f'<link rel="alternate" hreflang="x-default" '
                   f'href="{esc(base)}/{esc(groups[g][DEFAULT_LANG])}.html">')
    return "\n".join(out)

def gsc_meta():
    code = SITE.get("gsc_verification", "")
    return f'<meta name="google-site-verification" content="{esc(code)}">' if code else ""

def analytics_snippet():
    ga = SITE.get("ga_id", "")
    if not ga:
        return ""
    return (f'<script async src="https://www.googletagmanager.com/gtag/js?id={esc(ga)}"></script>\n'
            f'<script>window.dataLayer=window.dataLayer||[];'
            f'function gtag(){{dataLayer.push(arguments);}}'
            f'gtag("js",new Date());gtag("config","{esc(ga)}");</script>')

# ---------- structured data ----------

def jsonld(page):
    canonical = f"{SITE['base_url']}/{page['slug']}.html"
    article = {
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "headline": page["h1"],
        "description": page["meta_description"],
        "inLanguage": page_lang(page),
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

def _logo_parts():
    name = SITE["name"]
    m = re.match(r"(.*?)([A-Z][a-z]+)$", name)
    return (m.group(1), m.group(2)) if m else (name, "")

def build_page(page, lookup, groups):
    lang = page_lang(page)
    strings = strings_for(lang)
    canonical = f"{SITE['base_url']}/{page['slug']}.html"
    prefix, suffix = _logo_parts()

    draft = ""
    if page.get("_draft"):
        draft = ('<div class="draft">DRAFT — generated skeleton. '
                 'Fill the body before publishing (run generate_content.py or write by hand).</div>')

    repl = {
        "{{LANG}}": esc(lang),
        "{{DIR}}": page_dir(page),
        "{{TITLE}}": esc(page["title"]),
        "{{META_DESCRIPTION}}": esc(page["meta_description"]),
        "{{CANONICAL}}": esc(canonical),
        "{{HREFLANG}}": hreflang(page, groups),
        "{{GSC_VERIFICATION}}": gsc_meta(),
        "{{ANALYTICS}}": analytics_snippet(),
        "{{JSONLD}}": jsonld(page),
        "{{SITE_PREFIX}}": esc(prefix),
        "{{SITE_SUFFIX}}": esc(suffix),
        "{{SITE_NAME}}": esc(SITE["name"]),
        "{{TAGLINE}}": esc(strings.get("tagline", SITE["tagline"])),
        "{{TYPE}}": esc(page["type"]),
        "{{TYPE_LABEL}}": esc(strings["type_labels"].get(page["type"], page["type"])),
        "{{SLUG}}": esc(page["slug"]),
        "{{H1}}": esc(page["h1"]),
        "{{DRAFT_NOTICE}}": draft,
        "{{INTRO}}": esc(page["intro"]),
        "{{UPDATED_LABEL}}": esc(strings["updated"]),
        "{{UPDATED}}": esc(page.get("updated", TODAY)),
        "{{BY_LABEL}}": esc(strings["by"]),
        "{{AUTHOR}}": esc(SITE["author"]),
        "{{LANGS}}": render_langs(page, groups),
        "{{BODY}}": render_blocks(page.get("blocks", [])),
        "{{AD}}": render_ad(page.get("affiliate"), lang, strings),
        "{{FAQ}}": render_faq(page.get("faq", []), strings),
        "{{RELATED}}": render_related(page.get("related", []), lookup, strings),
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

def build_index(pages, groups):
    """Home page lists the default-language pages grouped by type."""
    strings = strings_for(DEFAULT_LANG)
    en_pages = [p for p in pages if page_lang(p) == DEFAULT_LANG]
    by_type = {}
    for p in en_pages:
        by_type.setdefault(p["type"], []).append(p)

    sections = []
    for typ, label in strings["type_labels"].items():
        if typ not in by_type:
            continue
        links = "".join(
            f'<a href="{esc(p["slug"])}.html"><span>→</span>{esc(p["h1"])}'
            + (' <em style="color:#b08900;font-style:normal">· draft</em>' if p.get("_draft") else "")
            + "</a>"
            for p in by_type[typ]
        )
        sections.append(f'<div class="related"><div class="eyebrow">{esc(label)}</div>{links}</div>')

    prefix, suffix = _logo_parts()
    canonical = f"{SITE['base_url']}/index.html"
    repl = {
        "{{LANG}}": esc(DEFAULT_LANG), "{{DIR}}": "ltr",
        "{{TITLE}}": esc(f"{SITE['name']} — {SITE['tagline']}"),
        "{{META_DESCRIPTION}}": esc(SITE["tagline"]),
        "{{CANONICAL}}": esc(canonical), "{{HREFLANG}}": "",
        "{{GSC_VERIFICATION}}": gsc_meta(), "{{ANALYTICS}}": analytics_snippet(),
        "{{JSONLD}}": "",
        "{{SITE_PREFIX}}": esc(prefix), "{{SITE_SUFFIX}}": esc(suffix),
        "{{SITE_NAME}}": esc(SITE["name"]), "{{TAGLINE}}": esc(SITE["tagline"]),
        "{{TYPE}}": "home", "{{TYPE_LABEL}}": esc(strings.get("index_label", "Index")),
        "{{SLUG}}": "", "{{H1}}": esc(SITE["name"]), "{{DRAFT_NOTICE}}": "",
        "{{INTRO}}": esc(SITE["tagline"]),
        "{{UPDATED_LABEL}}": esc(strings["updated"]), "{{UPDATED}}": TODAY,
        "{{BY_LABEL}}": esc(strings["by"]), "{{AUTHOR}}": esc(SITE["author"]),
        "{{LANGS}}": "", "{{BODY}}": "", "{{AD}}": "", "{{FAQ}}": "",
        "{{RELATED}}": "".join(sections), "{{YEAR}}": str(YEAR),
    }
    html_out = TEMPLATE
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
    all_pages = DATA["pages"] + expand_matrix()
    lookup = {p["slug"]: p["h1"] for p in all_pages}

    groups = {}
    for p in all_pages:
        g = p.get("group")
        if g:
            groups.setdefault(g, {})[page_lang(p)] = p["slug"]

    for p in all_pages:
        build_page(p, lookup, groups)
    build_index(all_pages, groups)
    build_sitemap(all_pages)

    drafts = sum(1 for p in all_pages if p.get("_draft"))
    full = len(all_pages) - drafts
    by_lang = {}
    for p in all_pages:
        by_lang[page_lang(p)] = by_lang.get(page_lang(p), 0) + 1
    langs = ", ".join(f"{k}:{v}" for k, v in sorted(by_lang.items()))
    print(f"[built] {len(all_pages)} pages -> {OUT}/")
    print(f"  - {full} full pages ready to publish")
    print(f"  - {drafts} skeleton pages need content before publishing")
    print(f"  - languages: {langs}")
    print(f"  - index.html + sitemap.xml generated")

if __name__ == "__main__":
    main()
