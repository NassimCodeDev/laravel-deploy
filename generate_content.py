#!/usr/bin/env python3
"""
generate_content.py — draft real content for the skeleton (matrix) pages.

The matrix in keywords.json creates many pages with empty bodies. Thin pages
get penalized by search engines, so each one needs real content before you
publish it. This script asks Claude to draft that content as structured blocks,
which you then review and paste back into keywords.json (as a full page entry).

Set your key first:   export ANTHROPIC_API_KEY=sk-ant-...
Install the SDK:       pip install anthropic
Run:                   python3 generate_content.py "send email with Mailable" howto

It prints a JSON block ready to drop into the "pages" array. ALWAYS read and
edit the draft before publishing — your real experience is what makes the page
rank and convert. Treat the model's output as a first draft, not final copy.
"""

import sys, json, os

MODEL = "claude-sonnet-4-6"

SYSTEM = (
    "You write accurate, concise technical guides for Laravel 11 developers. "
    "Use copy-paste-ready code. Be specific, never padded. "
    "Respond ONLY with a JSON object, no markdown fences, no preamble."
)

def prompt(topic, ptype):
    shape = (
        '{"intro": "2-3 sentence intro", '
        '"blocks": [{"type":"h2","text":""},{"type":"p","text":""},'
        '{"type":"code","lang":"php","text":""}], '
        '"faq": [{"q":"","a":""}]}'
    )
    kind = "how-to guide" if ptype == "howto" else "troubleshooting fix"
    return (
        f"Write a {kind} for Laravel 11 on the topic: \"{topic}\".\n"
        f"Return JSON exactly in this shape: {shape}\n"
        "Use 3-5 h2 sections, real code blocks with correct lang tags "
        "(bash/php/nginx/ini), and 2-3 FAQ entries. Keep it tight and practical."
    )

def main():
    if len(sys.argv) < 3:
        print('usage: python3 generate_content.py "<topic>" <howto|fix>')
        sys.exit(1)
    topic, ptype = sys.argv[1], sys.argv[2]

    try:
        from anthropic import Anthropic
    except ImportError:
        print("Install the SDK first:  pip install anthropic")
        sys.exit(1)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Set your key first:  export ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)

    client = Anthropic()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt(topic, ptype)}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    text = text.replace("```json", "").replace("```", "").strip()

    try:
        draft = json.loads(text)
    except json.JSONDecodeError:
        print("Model did not return clean JSON. Raw output:\n")
        print(text)
        sys.exit(1)

    print("\n# Review and edit, then paste into the \"pages\" array of keywords.json:\n")
    print(json.dumps(draft, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
