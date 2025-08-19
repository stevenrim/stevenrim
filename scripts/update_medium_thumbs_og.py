import re
import html
import pathlib
import feedparser
import requests
from datetime import datetime

FEED_URL = "https://medium.com/feed/@stevenrim"
README = pathlib.Path("README.md")
START_MARK = "<!-- MEDIUM-OG:START -->"
END_MARK   = "<!-- MEDIUM-OG:END -->"

# Fallback icon if a cover can't be found
FALLBACK_IMG = "https://cdn-icons-png.flaticon.com/512/5968/5968906.png"

# A conservative UA helps avoid 403s
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

def fetch_og_image(url: str, timeout=10) -> str:
    """Fetch page HTML and extract <meta property="og:image" ...> (or twitter:image)."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        r.raise_for_status()
        html_text = r.text

        # Try og:image first
        m = re.search(r'<meta\s+(?:property|name)=["\']og:image["\']\s+content=["\']([^"\']+)["\']', html_text, re.IGNORECASE)
        if m and m.group(1):
            return m.group(1)

        # Fallback: twitter:image
        m = re.search(r'<meta\s+(?:property|name)=["\']twitter:image["\']\s+content=["\']([^"\']+)["\']', html_text, re.IGNORECASE)
        if m and m.group(1):
            return m.group(1)
    except Exception:
        pass
    return FALLBACK_IMG

def extract_date(entry) -> str:
    if entry.get("published_parsed"):
        dt = datetime(*entry.published_parsed[:6])
        return dt.strftime("%Y-%m-%d")
    if entry.get("updated_parsed"):
        dt = datetime(*entry.updated_parsed[:6])
        return dt.strftime("%Y-%m-%d")
    return ""

def build_table(entries, max_items=10, thumb_width=120) -> str:
    """Build a GitHub-safe HTML table: [thumbnail] [Title + date]."""
    rows = []
    for e in entries[:max_items]:
        title = html.escape(e.title or "Untitled")
        link = e.link
        date = extract_date(e)

        # Pull consistent cover image from the article page
        img = fetch_og_image(link) or FALLBACK_IMG

        row_html = f"""
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
        rows.append(row_html)

    if not rows:
        return "<p>(No items found in Medium feed.)</p>"

    return "<table>\n" + "\n".join(rows) + "\n</table>"

def replace_between_markers(text: str, start: str, end: str, replacement: str) -> str:
    pattern = re.compile(rf"({re.escape(start)})(.*)({re.escape(end)})", re.DOTALL)
    return pattern.sub(rf"\1\n{replacement}\n\3", text)

def main():
    feed = feedparser.parse(FEED_URL)
    html_block = build_table(feed.entries, max_items=10, thumb_width=120)

    md = README.read_text(encoding="utf-8")
    new_md = replace_between_markers(md, START_MARK, END_MARK, html_block)

    if new_md != md:
        README.write_text(new_md, encoding="utf-8")
        print("README updated with Medium thumbnails via OpenGraph.")
    else:
        print("No changes.")

if __name__ == "__main__":
    main()
