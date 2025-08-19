import re
import html
import pathlib
import feedparser
from datetime import datetime

FEED_URL = "https://medium.com/feed/@stevenrim"  # your page
README = pathlib.Path("README.md")
START_MARK = "<!-- MEDIUM-LIST:START -->"
END_MARK = "<!-- MEDIUM-LIST:END -->"

# A small Medium placeholder icon in case a post has no image
FALLBACK_IMG = "https://cdn-icons-png.flaticon.com/512/5968/5968906.png"

def extract_image(entry):
    # Prefer media tags
    if "media_thumbnail" in entry and entry.media_thumbnail:
        url = entry.media_thumbnail[0].get("url")
        if url: return url
    if "media_content" in entry and entry.media_content:
        url = entry.media_content[0].get("url")
        if url: return url

    # Fallback: find first <img> in content/summary
    html_blob = ""
    if entry.get("content"):
        html_blob = entry.content[0].value
    elif entry.get("summary"):
        html_blob = entry.summary

    m = re.search(r'<img[^>]+src="([^"]+)"', html_blob or "")
    return m.group(1) if m else None

def extract_date(entry):
    # Try common fields
    if entry.get("published_parsed"):
        dt = datetime(*entry.published_parsed[:6])
        return dt.strftime("%Y-%m-%d")
    if entry.get("updated_parsed"):
        dt = datetime(*entry.updated_parsed[:6])
        return dt.strftime("%Y-%m-%d")
    return ""

def build_table(entries, max_items=12, thumb_width=120):
    """
    Builds a simple HTML table with:
    [thumbnail] [Title (link)]
                 [date]
    Using a <table> is GitHub-safe (no CSS needed).
    """
    rows = []
    for e in entries[:max_items]:
        title = html.escape(e.title or "Untitled")
        link = e.link
        date = extract_date(e)
        img = extract_image(e) or FALLBACK_IMG

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

    table = "<table>\n" + "\n".join(rows) + "\n</table>"
    return table

def replace_between_markers(text, start, end, replacement):
    pattern = re.compile(rf"({re.escape(start)})(.*)({re.escape(end)})", re.DOTALL)
    return pattern.sub(rf"\1\n{replacement}\n\3", text)

def main():
    feed = feedparser.parse(FEED_URL)
    html_block = build_table(feed.entries, max_items=12, thumb_width=120)

    md = README.read_text(encoding="utf-8")
    new_md = replace_between_markers(md, START_MARK, END_MARK, html_block)

    if new_md != md:
        README.write_text(new_md, encoding="utf-8")
        print("README updated with Medium thumbnails + titles.")
    else:
        print("No changes.")

if __name__ == "__main__":
    main()
