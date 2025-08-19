import os, re, html, pathlib, feedparser, requests
from datetime import datetime
from html import unescape

FEED_URL   = os.getenv("FEED_URL", "https://medium.com/feed/@stevenrim")
README     = pathlib.Path("README.md")

# Robust marker regex (tolerates whitespace)
START_RE   = r"<!--\s*MEDIUM-OG:START\s*-->"
END_RE     = r"<!--\s*MEDIUM-OG:END\s*-->"

FALLBACK_IMG = "https://cdn-icons-png.flaticon.com/512/5968/5968906.png"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
}

def extract_date(entry):
    for key in ("published_parsed", "updated_parsed"):
        if entry.get(key):
            dt = datetime(*entry[key][:6])
            return dt.strftime("%Y-%m-%d")
    return ""

def first_img_from_content(entry_html: str):
    if not entry_html:
        return None
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', entry_html, re.IGNORECASE)
    return m.group(1) if m else None

def fetch_og_image(url: str, timeout=10) -> str | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        r.raise_for_status()
        t = r.text
        # Try multiple meta variations
        for key in ("og:image:secure_url", "og:image", "twitter:image"):
            m = re.search(
                rf'<meta\b[^>]*?(?:property|name)\s*=\s*["\']{re.escape(key)}["\'][^>]*?content\s*=\s*["\']([^"\']+)["\']',
                t, re.IGNORECASE
            )
            if m:
                return m.group(1)
    except Exception:
        pass
    return None

def replace_between(text: str, start_re: str, end_re: str, replacement: str) -> str:
    pattern = re.compile(f"({start_re})(.*)({end_re})", re.DOTALL | re.IGNORECASE)
    if not re.search(pattern, text):
        raise SystemExit("ERROR: README markers not found or mismatched.")
    return re.sub(pattern, rf"\1\n{replacement}\n\3", text)

def build_table(entries, max_items=10, thumb_width=120) -> str:
    rows = []
    used_og, used_fallback, total = 0, 0, 0

    for e in entries[:max_items]:
        total += 1
        title = html.escape(e.title or "Untitled")
        link  = e.link
        date  = extract_date(e)

        # 1) Try OpenGraph cover
        img = fetch_og_image(link)

        # 2) If OG missing/blocked, try first <img> from RSS content
        if not img:
            html_blob = ""
            if e.get("content"):
                html_blob = e.content[0].value
            elif e.get("summary"):
                html_blob = e.summary
            img = first_img_from_content(html_blob)

        # 3) If still nothing, use fallback icon
        if not img:
            img = FALLBACK_IMG
            used_fallback += 1
        elif img == FALLBACK_IMG:
            used_fallback += 1
        elif "medium.com" in link:
            used_og += 1

        row = f"""
<tr>
  <td>
    <a href="{link}">
      <img src="{img}" alt="{title}" width="{thumb_width}">
    </a>
  </td>
  <td>
    <a href="{link}"><strong>{title}</strong></a><br/>
    <sub>{date}</sub>
  </td>
</tr>""".strip()
        rows.append(row)

    table = "<table>\n" + "\n".join(rows) + "\n</table>" if rows else "<p>(No items)</p>"
    print(f"[medium-og] entries={total}, og_used≈{used_og}, fallbacks={used_fallback}")
    return table

def main():
    d = feedparser.parse(FEED_URL)
    if not d.entries:
        raise SystemExit("ERROR: No entries parsed from Medium feed.")
    block = build_table(d.entries, max_items=10, thumb_width=120)

    md = README.read_text(encoding="utf-8")
    new_md = replace_between(md, START_RE, END_RE, block)

    if new_md != md:
        README.write_text(new_md, encoding="utf-8")
        print("README updated ✅")
    else:
        print("No changes (content identical).")

if __name__ == "__main__":
    main()
