# LaravelDeploy — programmatic SEO MVP

A static-site engine for a Laravel developer reference site. You write the data
once; the script generates SEO-clean pages, internal links, schema, and a
sitemap. Monetization runs through **hosting affiliates** (high payout) plus your
own products and CODNET leads — never through coding tools that don't pay.

## Why this niche / this money model

- AI coding tools (Cursor, Copilot, Claude Code) mostly have **no affiliate
  program** → don't monetize on them.
- Developers searching "how to deploy Laravel on X" have **strong buying intent**
  for hosting. Cloudways / Hostinger / DigitalOcean pay **$25–$125 per signup**.
- You know the stack → you can write **real** content, which is what ranks.
- Arabic / French versions of the same pages = an almost empty competition lane.

## Run it

```bash
python build.py           # generates everything into output/
# (on macOS/Linux it may be: python3 build.py)
```

On Windows use `python` — `python3` there is a broken Microsoft Store stub.
Open `output/index.html` in a browser. That's the whole site.

## Live site & deploy

- **Live:** https://nassimcodedev.github.io/laravel-deploy/
- **Repo:** https://github.com/NassimCodeDev/laravel-deploy
- Hosted on **GitHub Pages**, built by **GitHub Actions** (`.github/workflows/deploy.yml`).
- The daily loop is now: edit `data/keywords.json` → `git push` → the Action runs
  `python build.py` and publishes `output/` automatically. No manual upload.
- `output/` is git-ignored on purpose — CI rebuilds it on every push.

## Files

```
data/keywords.json     ← the only file you edit day to day
templates/page.html    ← design + SEO scaffold (rarely touched)
build.py               ← the generator (pages, index, sitemap, schema)
generate_content.py    ← optional: draft skeleton pages via Claude API
output/                ← the generated static site (deploy this)
```

## How content is created

1. **Hand-authored pages** live in `pages[]` with full `blocks`. The 16 shipped
   pages (deploys, fixes, comparisons, how-tos) show the quality bar.
2. **Matrix pages** in `matrix{}` expand automatically: `tasks × pattern` and
   `errors × pattern`. These ship as **skeletons marked DRAFT** — correct SEO
   structure, empty body. Fill before publishing (thin pages get penalized).

To draft a skeleton's body:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
pip install anthropic
python3 generate_content.py "upload files to S3" howto
# review/edit the JSON it prints, paste into pages[] as a full entry, rebuild
```

## The actual daily loop (the "5 minutes")

The heavy lifting is the first week: write the 6+ real pages and wire the
matrix. After that:

1. Check which keywords are getting impressions (Google Search Console).
2. Add **one** new task or error to `matrix{}` (or promote a skeleton to a full
   page by filling its body).
3. `python3 build.py` → redeploy.

That's the 5-minute version — but only because the system was built first.

## Before you publish

- Replace every `YOUR_ID` in `data/keywords.json` affiliate URLs with your real
  affiliate IDs.
- Set the real domain in `site.base_url` (used by canonical tags + sitemap).
- Fill every DRAFT page or leave it unbuilt — never publish empty skeletons.
- Deploy `output/` to any static host (the irony: this site itself needs no PHP).
